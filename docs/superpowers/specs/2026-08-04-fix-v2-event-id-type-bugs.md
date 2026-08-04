# Fix V2 API Event, ID, and Type Bugs

> **Derived from:** Deep research audit of `BridgeEmulator/HueObjects/` and `BridgeEmulator/flaskUI/v2restapi.py`
>
> **Goal:** Fix pre-existing bugs across 4 patterns: premature constructor StreamEvents, wrong POST response rids, type casing overwrites, and event stream reliability. Implemented in 6 phases, ordered for testability.

## Root cause

Constructors fire `"add"` StreamEvents before the object is fully built (lights, children, lightstates not yet assigned). The V1 API does this correctly (`restful.py:241-260` builds the object, populates it, then fires one complete event). The V2 code never followed this pattern.

Every downstream symptom — duplicate rooms, invisible entertainment areas, empty scenes, wrong resource IDs — traces to this one design flaw, amplified by an unreliable event stream that destructively clears events without confirming delivery.

## Execution order

Phases ordered for testability: fix the event stream first (so we can verify other fixes), then fix event content, then IDs/types, then DELETE/misc.

**Phase 4 → Phase 1 → Phase 2 → Phase 3 → Phase 5 → Phase 6**

---

## Phase 4: Fix event stream reliability (DO FIRST)

**File:** `services/eventStreamer.py`

Without this, correct events from Phases 1-3 can still be dropped by the broker, making those fixes appear broken.

### 4a. Replace destructive-clear with per-connection queues

`messageBroker()` clears `HueObjects.eventstream = []` every ~0.5s regardless of whether any SSE client consumed the events.

**Design:** Each SSE generator gets its own `collections.deque` (with `maxlen` to bound memory). `StreamEvent()` (in `HueObjects/__init__.py`) appends the event to all active queues under a `threading.Lock`. When a client disconnects (`GeneratorExit`), its queue is deregistered in a `finally` block. The `messageBroker` thread is removed entirely — no more global list clearing.

**SSE format must be preserved:** Each SSE frame is `id: <counter>\ndata: [<single event dict>]\n\n`. The generator iterates its private deque, yielding one event per frame.

**Thread safety:** Flask runs POST handlers and SSE generators in separate threads. `StreamEvent()` acquires a lock to iterate the active-queue list and append. The SSE generator pops from its own deque (single-consumer, no lock needed).

### 4b. Remove the 1000-iteration cap

Line 24: `counter = 1000` self-terminates SSE connections after ~200-400s. Remove this limit — let the connection run until the client disconnects.

### 4c. Remove the dead V1 eventstream sink

`restful.py:260` appends to `bridgeConfig["temp"]["eventstream"]` — a list no consumer ever reads. Remove this line. The V1 `StreamEvent` calls at `restful.py:241-260` already flow through the global `HueObjects.eventstream`, so events are preserved.

---

## Phase 1: Move "add" StreamEvents out of constructors

**Principle:** Constructors must not fire StreamEvents. POST handlers fire exactly one complete `"type": "add"` event after the object is fully built and inserted into `bridgeConfig`.

### 1a. `Group.__init__` — `HueObjects/Group.py:27-32`

- **Remove:** The `StreamEvent` block that fires `getV2Room()` or `getV2Zone()` with `"type": "add"`.
- **Add to:** `v2restapi.py` POST handler for `room`/`zone`, after `bridgeConfig["groups"][new_object_id] = newObject` and after all `add_light()` calls.
- **Event payload:** `newObject.getV2Room()` (if room) or `newObject.getV2Zone()` (if zone).
- **Gotcha:** `Group.add_light()` at Group.py:80-100 fires grouped_light add + room/zone update events. The room add event must fire BEFORE these child events — place it before the `if "children" in postDict:` block. A real Hue bridge fires the parent add first, then child updates; this ordering matches.

### 1b. `EntertainmentConfiguration.__init__` — `HueObjects/EntertainmentConfiguration.py:28-33`

- **Remove:** The `StreamEvent` block that fires `getV2Api()` with `"type": "add"` (currently fires with empty lights — `lights=[]`).
- **Replace the existing compensating `update` at** `v2restapi.py:523-527` **with a single `"type": "add"` event** carrying `newObject.getV2Api()`. This event already fires after lights/locations are assigned — just change the type to `"add"` and remove the constructor add. Do NOT add a second event.
- **Gotcha:** `EntertainmentConfiguration.add_light()` at lines 54-56 fires NO events (unlike `Group.add_light`). So this handler-level add is the only event for entertainment areas. That's correct — one complete add event, no redundant updates.
- **Cleanup:** Remove `print("x:", x)` debug leftover at `EntertainmentConfiguration.py:192`.

### 1c. `Scene.__init__` — `HueObjects/Scene.py:35-41`

- **Remove:** The `StreamEvent` block (fires `getV2Api()` twice — line 36 for the event, line 40 via `.update()`). Removing the block removes both.
- **Add to:** `v2restapi.py` POST handler for `scene`, after `lightstates` are populated. **Must be placed OUTSIDE the `if "actions" in postDict:` block** (ends at line 485), otherwise a GroupScene without explicit "actions" fires no event. Place after line 461 (`bridgeConfig["scenes"][new_object_id] = newObject`) or after the actions block.
- **Event payload:** `newObject.getV2Api()`.
- **Adjacent fix:** `postDict["lights"]` overwrites the resolved light objects in `objCreation["lights"]` via `objCreation.update(postDict)` at line 459 — delete `postDict["lights"]` before the update (matching the existing `del postDict["group"]` at line 452).

### 1d. `SmartScene.__init__` — `HueObjects/SmartScene.py:29-35`

- **Remove:** The `StreamEvent` block.
- **Add to:** `v2restapi.py` POST handler for `smart_scene`, after `bridgeConfig["smart_scene"][new_object_id] = newObject`.
- **Event payload:** `newObject.getV2Api()`.

### 1e. `BehaviorInstance.__init__` — `HueObjects/BehaviorInstance.py:18-23`

- **Remove:** The `StreamEvent` block.
- **Also fix KeyError guards:** `data["metadata"]["name"]` (line 12) → `data.get("metadata", {}).get("name", "")`, `data["configuration"]` (line 13) → `data.get("configuration", {})`, `self.configuration["where"]` (line 51) → `self.configuration.get("where", {})`.
- **Add to:** `v2restapi.py` POST handler for `behavior_instance`, after `bridgeConfig["behavior_instance"][newObject.id_v2] = newObject`.
- **Event payload:** `newObject.getV2Api()`.

### 1f. `GeofenceClient.__init__` — `HueObjects/GeofenceClient.py:14-20`

- **Remove:** The `StreamEvent` block.
- **Add `id_v1` storage:** `self.id_v1 = data["id_v1"]` in the constructor (needed for DELETE — see Phase 5b).
- **Add to:** `v2restapi.py` POST handler for `geofence_client`, after `bridgeConfig["geofence_clients"][new_object_id] = newObject`.
- **Event payload:** `newObject.getV2GeofenceClient()`.

### 1g. `Sensor.__init__` — `HueObjects/Sensor.py:53-60`

- **Keep:** The `device` add event (sensor data is complete at construction time).
- **Add:** Sub-resource add events for motion, light_level, temperature, button, and relative_rotary alongside the device add — since sub-resource data is also complete at construction time (no separate POST handler for sensors). Use the same pattern: fire `getMotion()`/`getTemperature()`/etc. based on `self.type`.

### 1h. `Light.__init__` — `HueObjects/Light.py:31-64`

- **No structural changes.** All data available at construction time.
- **Fix:** `"entertainent"` → `"entertainment"` typo at line 33.

---

## Phase 2: Fix POST response `rid`

**File:** `v2restapi.py:567-570`

The current `returnMessage` returns `newObject.id_v2` for all resources. This is wrong for resources where the V2 ID is derived via `uuid5(base, suffix)`.

**Add a lookup dict** (module-level, near `v2Resources`):

```python
_POST_RID_SUFFIX = {
    "room": "room",
    "zone": "zone",
    "entertainment_configuration": "entertainment_configuration",
    "geofence_client": "geofence_client",
}
```

**In the return:**

```python
rid = newObject.id_v2
suffix = _POST_RID_SUFFIX.get(resource)
if suffix:
    rid = str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + suffix))
returnMessage = {"data": [{"rid": rid, "rtype": resource}], "errors": []}
```

Resources not in the dict (scene, smart_scene, behavior_instance) use `id_v2` as-is (already correct).

---

## Phase 3: Fix type casing

**File:** `v2restapi.py` POST handler

In every POST branch, `objCreation.update(postDict)` overwrites the canonical `type` with whatever the client sends (often lowercase). Fix by popping `type` from `postDict` before the update:

```python
postDict.pop("type", None)  # don't let client overwrite canonical type
objCreation.update(postDict)
```

**Apply to:** `room`, `zone`, `entertainment_configuration`, `scene` branches. `smart_scene` and `behavior_instance` are safe (type hardcoded in `getV2Api`).

---

## Phase 5: Fix DELETE handler bugs

**File:** `v2restapi.py:750-774`

### 5a. smart_scene DELETE

`bridgeConfig["smart_scene"]` is keyed by numeric `id_v1`, but DELETE passes V2 `id_v2`. `getObject` already resolves the object — use `del bridgeConfig["smart_scene"][object.id_v1]`.

### 5b. geofence_client DELETE

Dict key is `"geofence_clients"` (plural), but the handler uses `resource` = `"geofence_client"` (singular). `getObject` already resolved the object — use `del bridgeConfig["geofence_clients"][object.id_v1]`. This requires Phase 1f's `id_v1` storage fix.

### 5c. Sub-resource DELETE must NOT delete the parent

The following resource types resolve via `getObject` to parent objects and would delete the entire parent: `motion`, `temperature`, `light_level`, `button`, `relative_rotary`, `device_power`, `grouped_light`. For these, return an error (`400` or `405`) instead of deleting the parent. Real Hue returns 405 for sub-resource DELETE.

### 5d. Clean v2Resources cache

After deletion, remove the entry from `v2Resources[resource]` if present.

### 5e. Delete events

Skip explicit delete events — `__del__` on Group/Scene/SmartScene/etc. already fires them. Phase 4's reliable event delivery makes them actually reach clients. If doubles appear, remove `__del__` blocks in a follow-up.

---

## Phase 6: Misc fixes

| Bug | File | Fix |
|-----|------|-----|
| BehaviorInstance KeyError (`metadata.name`) | `BehaviorInstance.py:12` | `data.get("metadata", {}).get("name", "")` |
| BehaviorInstance KeyError (`configuration`) | `BehaviorInstance.py:13` | `data.get("configuration", {})` |
| BehaviorInstance KeyError (`configuration.where`) | `BehaviorInstance.py:51` | `self.configuration.get("where", {})` |
| Light "entertainent" typo | `Light.py:33` | `"entertainent"` → `"entertainment"` |
| v2Resources dead weakrefs | `v2restapi.py:30-32` | Check `ref() is not None`; if None, delete cache entry and fall through to re-populate |
| Sensor sub-resource add events | `Sensor.py:53-60` | Fire in constructor alongside device add (data is complete) |
| `print("x:", x)` debug leftover | `EntertainmentConfiguration.py:192` | Remove |

---

## Files modified

| File | Phases |
|------|--------|
| `BridgeEmulator/services/eventStreamer.py` | 4 |
| `BridgeEmulator/HueObjects/__init__.py` | 4 |
| `BridgeEmulator/HueObjects/Group.py` | 1a |
| `BridgeEmulator/HueObjects/EntertainmentConfiguration.py` | 1b, 6 |
| `BridgeEmulator/HueObjects/Scene.py` | 1c |
| `BridgeEmulator/HueObjects/SmartScene.py` | 1d |
| `BridgeEmulator/HueObjects/BehaviorInstance.py` | 1e, 6 |
| `BridgeEmulator/HueObjects/GeofenceClient.py` | 1f |
| `BridgeEmulator/HueObjects/Sensor.py` | 1g, 6 |
| `BridgeEmulator/HueObjects/Light.py` | 1h, 6 |
| `BridgeEmulator/flaskUI/v2restapi.py` | 1, 2, 3, 5, 6 |
| `BridgeEmulator/flaskUI/restful.py` | 4c |

## Verification

1. Create room → no duplicate in app, correct `rid` in POST response, visible immediately in GET
2. Create room via V1 API → still emits events and appears (restful.py path)
3. Create entertainment area → visible in app immediately (no restart needed)
4. Create scene via V2 → actions populated, visible immediately
5. Delete smart_scene via V2 → no crash, resource removed
6. Delete geofence_client via V2 → no crash, resource removed (requires id_v1 storage)
7. Delete motion → returns error, parent sensor untouched
8. Type casing: room created with lowercase `"type":"room"` → displays as room (not zone), visible in GET /room
9. Event stream: events not dropped, no duplicate or missing resources in app
10. Two simultaneous SSE clients both receive every event
11. SSE connection stays alive > 400s (no 1000-iteration cap)
12. behavior_instance POST without `"where"` → doesn't crash
13. DELETE then re-POST same resource → fresh object returned (v2Resources cache cleaned)
14. Server restart after all creates → everything persists correctly, no ghosts
