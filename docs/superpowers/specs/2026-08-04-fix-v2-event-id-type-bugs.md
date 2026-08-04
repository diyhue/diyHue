# Fix V2 API Event, ID, and Type Bugs

> **Derived from:** Deep research audit of `BridgeEmulator/HueObjects/` and `BridgeEmulator/flaskUI/v2restapi.py`
>
> **Goal:** Fix 14 pre-existing bugs across 4 patterns: premature constructor StreamEvents, wrong POST response rids, type casing overwrites, and event stream reliability.

## Root cause

Constructors fire `"add"` StreamEvents before the object is fully built (lights, children, lightstates not yet assigned). The V1 API does this correctly (`restful.py:241-260` builds the object, populates it, then fires one complete event). The V2 code never followed this pattern.

Every downstream symptom — duplicate rooms, invisible entertainment areas, empty scenes, wrong resource IDs — traces to this one design flaw, amplified by an unreliable event stream that destructively clears events without confirming delivery.

---

## Phase 1: Move "add" StreamEvents out of constructors

**Principle:** Constructors must not fire StreamEvents. POST handlers fire exactly one complete `"type": "add"` event after the object is fully built and inserted into `bridgeConfig`.

### 1a. `Group.__init__` — `HueObjects/Group.py:27-32`

- **Remove:** The `StreamEvent` block that fires `getV2Room()` or `getV2Zone()` with `"type": "add"`.
- **Add to:** `v2restapi.py` POST handler for `room`/`zone`, after `bridgeConfig["groups"][new_object_id] = newObject` and after all `add_light()` calls.
- **Event payload:** `newObject.getV2Room()` (if room) or `newObject.getV2Zone()` (if zone).

### 1b. `EntertainmentConfiguration.__init__` — `HueObjects/EntertainmentConfiguration.py:28-33`

- **Remove:** The `StreamEvent` block that fires `getV2Api()` with `"type": "add"` (currently fires with empty lights).
- **Replace the existing compensating `update` at** `v2restapi.py:523-527` **with a single `"type": "add"` event** carrying `newObject.getV2Api()`. This event already fires after lights/locations are assigned — just change the type and remove the constructor add.

### 1c. `Scene.__init__` — `HueObjects/Scene.py:35-41`

- **Remove:** The `StreamEvent` block.
- **Add to:** `v2restapi.py` POST handler for `scene`, after `lightstates` are populated (after the actions loop at lines 463-485).
- **Event payload:** `newObject.getV2Api()`.

### 1d. `SmartScene.__init__` — `HueObjects/SmartScene.py:29-35`

- **Remove:** The `StreamEvent` block.
- **Add to:** `v2restapi.py` POST handler for `smart_scene`, after `bridgeConfig["smart_scene"][new_object_id] = newObject`.
- **Event payload:** `newObject.getV2Api()`.

### 1e. `BehaviorInstance.__init__` — `HueObjects/BehaviorInstance.py:18-23`

- **Remove:** The `StreamEvent` block.
- **Also fix:** Guard access to `self.configuration["where"]` — use `.get("where", {})` to prevent `KeyError` when POST body lacks `"where"`.
- **Add to:** `v2restapi.py` POST handler for `behavior_instance`, after `bridgeConfig["behavior_instance"][newObject.id_v2] = newObject`.
- **Event payload:** `newObject.getV2Api()`.

### 1f. `GeofenceClient.__init__` — `HueObjects/GeofenceClient.py:14-20`

- **Remove:** The `StreamEvent` block.
- **Add to:** `v2restapi.py` POST handler for `geofence_client`, after `bridgeConfig["geofence_clients"][new_object_id] = newObject`.
- **Event payload:** `newObject.getV2GeofenceClient()`.

### 1g. `Sensor.__init__` — `HueObjects/Sensor.py:53-60`

- **Keep:** The `device` add event (sensor data is complete at construction time).
- **Add:** Sub-resource add events in the appropriate handlers for motion, light_level, temperature, button, relative_rotary device types.

### 1h. `Light.__init__` — `HueObjects/Light.py:31-64`

- **No changes.** All data available at construction time. Fix the `"entertainent"` → `"entertainment"` typo at line 33.

---

## Phase 2: Fix POST response `rid`

**File:** `v2restapi.py:567-570`

The current `returnMessage` returns `newObject.id_v2` for all resources. This is wrong for resources where the V2 ID is derived via `uuid5(base, suffix)`.

**Change to:**

| Resource | Return `rid` |
|----------|-------------|
| `room` | `str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + 'room'))` |
| `zone` | `str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + 'zone'))` |
| `entertainment_configuration` | `str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + 'entertainment_configuration'))` |
| `geofence_client` | `str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + 'geofence_client'))` |
| `scene`, `smart_scene`, `behavior_instance` | `newObject.id_v2` (unchanged — correct) |

**Implementation:** Add a helper mapping `rtype` → V2 ID, or inline the logic. Prefer a dict lookup over chained if/elif.

---

## Phase 3: Fix type casing

**File:** `v2restapi.py` POST handler

In every POST branch, `objCreation.update(postDict)` overwrites the canonical `type` with whatever the client sends (often lowercase). Fix by popping `type` from `postDict` before the update, or normalizing in constructors.

**Approach:** At the top of each branch where `type` is set canonically, strip it from `postDict` so `update()` can't overwrite it:

```python
postDict.pop("type", None)  # don't let client overwrite canonical type
objCreation.update(postDict)
```

Apply to: `room`, `zone`, `entertainment_configuration`, `scene` branches.

---

## Phase 4: Fix event stream reliability

**File:** `services/eventStreamer.py`

### 4a. Stop the destructive clear

`messageBroker()` at lines 10-17 clears `HueObjects.eventstream = []` every 0.3s regardless of whether any SSE client consumed the events. This is the amplifier for every event-related bug.

**Fix:** Replace the shared-list-plus-broker pattern with per-connection queues. Each SSE generator gets its own `collections.deque`. Objects publish events to all active queues. No events dropped unless a queue overflows.

**Alternative (simpler):** Keep the shared list but track a per-connection read cursor. `messageBroker` only trims events that all active connections have consumed.

### 4b. Remove the 1000-iteration cap

Line 24: `counter = 1000` self-terminates SSE connections after ~200-400s. Remove this limit — let the connection run until the client disconnects.

### 4c. Remove the dead V1 eventstream sink

`restful.py:260` appends to `bridgeConfig["temp"]["eventstream"]` — a list no consumer ever reads. Either wire it into the SSE stream or remove it.

---

## Phase 5: Fix DELETE handler bugs

**File:** `v2restapi.py:750-774`

### 5a. smart_scene DELETE

`bridgeConfig["smart_scene"]` is keyed by numeric `id_v1`, but the DELETE handler passes V2 `id_v2`. Fix: iterate to find the matching object by `id_v2`, delete by its `id_v1` key.

### 5b. geofence_client DELETE

Dict key is `"geofence_clients"` (plural), but the handler uses `resource` = `"geofence_client"` (singular). Fix: use the correct plural key, and look up by `id_v1`.

### 5c. Fire delete StreamEvents

After successful deletion, fire `{"type": "delete", "data": [{"id": resourceid, "type": resource}]}` for the deleted resource.

### 5d. Clean v2Resources cache

Remove the deleted object's entry from `v2Resources[resource]` if present.

---

## Phase 6: Misc fixes

| Bug | File | Fix |
|-----|------|-----|
| BehaviorInstance KeyError | `BehaviorInstance.py:51` | `self.configuration.get("where", {})` |
| Light "entertainent" typo | `Light.py:33` | `"entertainent"` → `"entertainment"` |
| v2Resources dead weakrefs | `v2restapi.py:30-32` | Check `ref() is not None` before returning; prune None entries |
| Sensor sub-resource events | `Sensor.py` | Fire add/delete for motion, temperature, light_level, button, relative_rotary |
| Sub-resource DELETE deletes parent | `v2restapi.py:757-762` | Don't delete parent sensor for sub-resource types; delete only the sub-resource attribute |

---

## Files modified

| File | Phases |
|------|--------|
| `BridgeEmulator/HueObjects/Group.py` | 1a |
| `BridgeEmulator/HueObjects/EntertainmentConfiguration.py` | 1b |
| `BridgeEmulator/HueObjects/Scene.py` | 1c |
| `BridgeEmulator/HueObjects/SmartScene.py` | 1d |
| `BridgeEmulator/HueObjects/BehaviorInstance.py` | 1e, 6 |
| `BridgeEmulator/HueObjects/GeofenceClient.py` | 1f |
| `BridgeEmulator/HueObjects/Sensor.py` | 1g, 6 |
| `BridgeEmulator/HueObjects/Light.py` | 1h, 6 |
| `BridgeEmulator/flaskUI/v2restapi.py` | 1, 2, 3, 5, 6 |
| `BridgeEmulator/services/eventStreamer.py` | 4 |
| `BridgeEmulator/flaskUI/restful.py` | 4c |

## Verification

1. Create room → no duplicate in app, correct `rid` in POST response, visible immediately in GET
2. Create entertainment area → visible in app immediately (no restart needed)
3. Create scene via V2 → actions populated, visible immediately
4. Delete smart_scene via V2 → no crash, resource removed
5. Delete geofence_client via V2 → no crash, resource removed
6. Type casing: room created with lowercase `"type":"room"` → displays as room (not zone), visible in GET /room
7. Event stream: events not dropped, no duplicate or missing resources in app
8. Server restart after all creates → everything persists correctly, no ghosts
