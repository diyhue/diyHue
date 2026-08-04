# Fix V2 API Event, ID, and Type Bugs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Fix pre-existing V2 API bugs: premature constructor StreamEvents, wrong POST response rids, type casing overwrites, and event stream reliability. Execution order: Phase 4 (event stream) → Phase 1 (move add events) → Phase 2 (fix POST rids) → Phase 3 (type casing) → Phase 5 (DELETE fixes) → Phase 6 (misc).

**Architecture:** Remove all `StreamEvent` "add" calls from constructors. Fire one complete "add" from POST handlers after full population. Replace the destructive-clear event broker with per-connection deques.

**Tech Stack:** Python stdlib: `threading.Lock`, `collections.deque`. Existing `uuid`, `StreamEvent`.

**Spec:** `docs/superpowers/specs/2026-08-04-fix-v2-event-id-type-bugs.md`

## Global Constraints

- Do NOT break the SSE wire format: `id: <counter>\ndata: [<single event dict>]\n\n`
- Do NOT break V1 API event behavior (`restful.py:241-260`)
- All `StreamEvent` calls removed from constructors must be re-added in POST handlers
- Phase 4 must ship first — without it, correct events can still be dropped

---

### Task 1: Phase 4 — Per-connection event queues

**Files:**
- Modify: `BridgeEmulator/services/eventStreamer.py`
- Modify: `BridgeEmulator/HueObjects/__init__.py`

**Interfaces:**
- Replaces: `HueObjects.eventstream = []` global list with `_event_queues: list[deque]` + `_event_lock: threading.Lock`
- Replaces: `StreamEvent(message)` function — now appends to all active queues under lock
- Removes: `messageBroker()` thread and its destructive clear
- Modifies: `streamV2Events()` generator — reads from private deque, no iteration cap

**Implementation:**

In `HueObjects/__init__.py`:
```python
import threading
from collections import deque

_event_queues = []
_event_lock = threading.Lock()

def StreamEvent(message):
    with _event_lock:
        for q in _event_queues:
            q.append(message)

def _register_queue(q):
    with _event_lock:
        _event_queues.append(q)

def _unregister_queue(q):
    with _event_lock:
        _event_queues.remove(q)
```

In `services/eventStreamer.py` — new `streamV2Events()`:
```python
import collections
from HueObjects import _register_queue, _unregister_queue

def streamV2Events():
    local_queue = collections.deque(maxlen=500)
    _register_queue(local_queue)
    try:
        counter = 0
        while True:
            if local_queue:
                messages = []
                while local_queue:
                    messages.append(local_queue.popleft())
                counter += 1
                yield f"id: {counter}\ndata: {json.dumps(messages, separators=(',', ':'))}\n\n"
            else:
                sleep(0.2)
    finally:
        _unregister_queue(local_queue)
```

Remove `messageBroker()` function entirely. Remove the `Thread(target=messageBroker).start()` call from `HueEmulator3.py:161`.

- [ ] Add `_event_queues`, `_event_lock`, `_register_queue`, `_unregister_queue` to `HueObjects/__init__.py`
- [ ] Rewrite `StreamEvent()` to append to all active queues under lock
- [ ] Rewrite `streamV2Events()` in `eventStreamer.py` with private deque, no cap
- [ ] Remove `messageBroker()` function from `eventStreamer.py`
- [ ] Remove `Thread(target=messageBroker).start()` from `HueEmulator3.py:161`
- [ ] Remove `from threading import Thread` from `eventStreamer.py` if no longer needed
- [ ] Remove `from time import sleep` and add `from time import sleep` if needed
- [ ] Commit: `fix: per-connection event queues, remove destructive messageBroker`

---

### Task 2: Phase 1a — Move Group add event to POST handler

**Files:**
- Modify: `BridgeEmulator/HueObjects/Group.py`
- Modify: `BridgeEmulator/flaskUI/v2restapi.py`

**Implementation:**

In `Group.py` — remove lines 27-32 (the `StreamEvent` block).

In `v2restapi.py` — in the `room`/`zone` POST branch, add the event BEFORE the `if "children"` block (so the room add fires before child grouped_light adds from `add_light`):

```python
elif resource in ["room", "zone"]:
    new_object_id = nextFreeId(bridgeConfig, "groups")
    objCreation = {...}
    postDict.pop("type", None)  # Phase 3 — don't let client overwrite canonical type
    objCreation["type"] = "Room" if resource == "room" else "Zone"
    ...
    newObject = Group.Group(objCreation)

    # Fire add event BEFORE children so parent exists before child updates
    streamMessage = {
        "creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": [newObject.getV2Room() if resource == "room" else newObject.getV2Zone()],
        "id": str(uuid.uuid4()),
        "type": "add"
    }
    StreamEvent(streamMessage)

    if "children" in postDict:
        ...
```

And after bridgeConfig insert + mark_dirty.

- [ ] Remove `StreamEvent` "add" block from `Group.py:27-32`
- [ ] Add `StreamEvent` "add" in v2restapi.py room/zone POST branch, before children loop
- [ ] Verify V1 room creation still works (separate path in restful.py)
- [ ] Commit: `fix: move Group add event from constructor to POST handler`

---

### Task 3: Phase 1b — Move EntertainmentConfiguration add event to POST handler

**Files:**
- Modify: `BridgeEmulator/HueObjects/EntertainmentConfiguration.py`
- Modify: `BridgeEmulator/flaskUI/v2restapi.py`

**Implementation:**

In `EntertainmentConfiguration.py` — remove lines 28-33 (the `StreamEvent` block). Also remove `print("x:", x)` at line 192.

In `v2restapi.py` — change the existing compensating `update` event (lines 523-527) to `"type": "add"`:

```python
# Before (lines 523-527):
streamMessage = {..., "type": "update"}
# After:
streamMessage = {..., "type": "add"}
```

- [ ] Remove `StreamEvent` "add" block from `EntertainmentConfiguration.py:28-33`
- [ ] Change `"type": "update"` to `"type": "add"` at `v2restapi.py:526`
- [ ] Remove `print("x:", x)` from `EntertainmentConfiguration.py:192`
- [ ] Commit: `fix: move EntertainmentConfiguration add event from constructor to POST handler`

---

### Task 4: Phase 1c — Move Scene add event to POST handler

**Files:**
- Modify: `BridgeEmulator/HueObjects/Scene.py`
- Modify: `BridgeEmulator/flaskUI/v2restapi.py`

**Implementation:**

In `Scene.py` — remove lines 35-41 (the `StreamEvent` block).

In `v2restapi.py` — add the add event OUTSIDE the `if "actions" in postDict:` block, after `bridgeConfig["scenes"][new_object_id] = newObject`:

```python
bridgeConfig["scenes"][new_object_id] = newObject
# Fire complete add event after lightstates populated
streamMessage = {
    "creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "data": [newObject.getV2Api()],
    "id": str(uuid.uuid4()),
    "type": "add"
}
StreamEvent(streamMessage)
configManager.bridgeConfig.mark_dirty("scenes")
```

Also fix the adjacent bug: `postDict["lights"]` overwrites resolved light objects — delete it before `objCreation.update(postDict)`:

```python
if "lights" in postDict:
    del postDict["lights"]  # don't overwrite resolved light objects
objCreation.update(postDict)
```

- [ ] Remove `StreamEvent` "add" block from `Scene.py:35-41`
- [ ] Add `StreamEvent` "add" in v2restapi.py scene POST branch, after lightstates + bridgeConfig insert
- [ ] Delete `postDict["lights"]` before `objCreation.update(postDict)` (adjacent fix)
- [ ] Commit: `fix: move Scene add event from constructor to POST handler`

---

### Task 5: Phase 1d, 1e, 1f — Move remaining constructor add events

**Files:**
- Modify: `BridgeEmulator/HueObjects/SmartScene.py`
- Modify: `BridgeEmulator/HueObjects/BehaviorInstance.py`
- Modify: `BridgeEmulator/HueObjects/GeofenceClient.py`
- Modify: `BridgeEmulator/flaskUI/v2restapi.py`

**Implementation:**

**SmartScene** — remove `StreamEvent` block from `SmartScene.py:29-35`. Add to POST handler after `bridgeConfig["smart_scene"][new_object_id] = newObject`.

**BehaviorInstance** — remove `StreamEvent` block from `BehaviorInstance.py:18-23`. Also guard `data["metadata"]["name"]` → `data.get("metadata", {}).get("name", "")`, `data["configuration"]` → `data.get("configuration", {})`, and `self.configuration["where"]` → `self.configuration.get("where", {})` in the constructor. Add event to POST handler after `bridgeConfig["behavior_instance"][newObject.id_v2] = newObject`.

**GeofenceClient** — remove `StreamEvent` block from `GeofenceClient.py:14-20`. Add `self.id_v1 = data["id_v1"]` to the constructor (needed for Phase 5 DELETE). Add event to POST handler after `bridgeConfig["geofence_clients"][new_object_id] = newObject`.

- [ ] Remove `StreamEvent` from `SmartScene.py:29-35`, add to v2restapi.py POST
- [ ] Remove `StreamEvent` from `BehaviorInstance.py:18-23`, add KeyError guards, add to v2restapi.py POST
- [ ] Remove `StreamEvent` from `GeofenceClient.py:14-20`, add `id_v1` storage, add to v2restapi.py POST
- [ ] Commit: `fix: move SmartScene, BehaviorInstance, GeofenceClient add events to POST handlers`

---

### Task 6: Phase 2 + Phase 3 — Fix POST rids and type casing

**Files:**
- Modify: `BridgeEmulator/flaskUI/v2restapi.py`

**Implementation:**

**Phase 2:** Add a module-level dict near `v2Resources`:

```python
_POST_RID_SUFFIX = {
    "room": "room",
    "zone": "zone",
    "entertainment_configuration": "entertainment_configuration",
    "geofence_client": "geofence_client",
}
```

Replace the return at ~line 567-570:

```python
rid = newObject.id_v2
suffix = _POST_RID_SUFFIX.get(resource)
if suffix:
    rid = str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + suffix))
returnMessage = {"data": [{"rid": rid, "rtype": resource}], "errors": []}
```

**Phase 3:** In the `room`/`zone` branch (already done in Task 2), `entertainment_configuration` branch, and `scene` branch, add `postDict.pop("type", None)` before `objCreation.update(postDict)`.

- [ ] Add `_POST_RID_SUFFIX` dict to v2restapi.py
- [ ] Replace returnMessage rid logic with suffix lookup
- [ ] Add `postDict.pop("type", None)` to room/zone (verify from Task 2), entertainment_configuration, scene branches
- [ ] Commit: `fix: correct POST response rids and prevent type casing overwrite`

---

### Task 7: Phase 5 — Fix DELETE handler bugs

**Files:**
- Modify: `BridgeEmulator/flaskUI/v2restapi.py`

**Implementation:**

Rewrite the DELETE handler at lines 750-774:

```python
def delete(self, resource, resourceid):
    authorisation = authorizeV2(request.headers)
    if "user" not in authorisation:
        return "", 403
    object = getObject(resource, resourceid)
    if not object:
        return {"errors": [{"description": f"Resource {resourceid} not found"}]}, 404

    # Sub-resource types: return error, don't delete parent
    _SUB_RESOURCES = {"motion", "temperature", "light_level", "button",
                      "relative_rotary", "device_power", "grouped_light"}
    if resource in _SUB_RESOURCES:
        return {"errors": [{"description": f"Cannot delete sub-resource: {resource}"}]}, 405

    if hasattr(object, 'getObjectPath'):
        v1_resource = object.getObjectPath()["resource"]
        v1_id = object.getObjectPath()["id"]
        del bridgeConfig[v1_resource][v1_id]
        configManager.bridgeConfig.mark_dirty(v1_resource)
    else:
        # smart_scene, behavior_instance — keyed differently
        yaml_resource = configManager.configHandler.Config.V2_TO_V1_RESOURCE.get(resource)
        if yaml_resource:
            del bridgeConfig[yaml_resource][object.id_v1]
            configManager.bridgeConfig.mark_dirty(yaml_resource)
        else:
            del bridgeConfig[resource][resourceid]

    # Clean v2Resources cache
    if resource in v2Resources and resourceid in v2Resources[resource]:
        del v2Resources[resource][resourceid]

    response = {"data": [{"rid": resourceid, "rtype": resource}]}
    return response
```

- [ ] Add sub-resource guard (return 405 for motion/button/etc.)
- [ ] Fix smart_scene to use `object.id_v1` for deletion
- [ ] Fix geofence_client to use `object.id_v1` for deletion (requires Phase 1f id_v1 storage)
- [ ] Add v2Resources cache cleanup
- [ ] Commit: `fix: DELETE handler — sub-resource guard, smart_scene/geofence_client keys, cache cleanup`

---

### Task 8: Phase 1g, 1h, Phase 6 — Sensor sub-resource events, Light typo, v2Resources fix

**Files:**
- Modify: `BridgeEmulator/HueObjects/Sensor.py`
- Modify: `BridgeEmulator/HueObjects/Light.py`
- Modify: `BridgeEmulator/flaskUI/v2restapi.py`
- Modify: `BridgeEmulator/flaskUI/restful.py`

**Implementation:**

**Sensor.py:** In `__init__`, alongside the existing device add, fire sub-resource add events:
```python
# Existing device add (keep)
if self.getDevice() is not None:
    streamMessage = {..., "data": [self.getDevice()], "type": "add"}
    StreamEvent(streamMessage)
# New: sub-resource add events
sub_resource_methods = {
    "ZLLLightLevel": "getLightlevel",
    "ZLLTemperature": "getTemperature",
    "ZLLPresence": "getMotion",
    "ZLLSwitch": "getButtons",
    "ZLLRelativeRotary": "getRotary",
}
method = sub_resource_methods.get(self.type)
if method:
    streamMessage = {..., "data": [getattr(self, method)()], "type": "add"}
    StreamEvent(streamMessage)
```

**Light.py:** Fix `"entertainent"` → `"entertainment"` at line 33.

**v2restapi.py:** Fix `getObject` dead weakref handling at line 30-32:
```python
if resourceid in v2Resources[resource]:
    obj = v2Resources[resource][resourceid]()
    if obj is not None:
        return obj
    del v2Resources[resource][resourceid]  # prune dead ref, fall through
```

**restful.py:** Remove the dead `bridgeConfig["temp"]["eventstream"].append(event)` line (line 260).

- [ ] Add sub-resource add events to `Sensor.__init__`
- [ ] Fix `"entertainent"` typo in `Light.py:33`
- [ ] Fix v2Resources dead weakref in `v2restapi.py:30-32`
- [ ] Remove dead V1 eventstream sink from `restful.py:260`
- [ ] Commit: `fix: sensor sub-resource events, Light typo, v2Resources cache, dead eventstream sink`

---

### Task 9: Integration test

**Test steps (manual):**

- [ ] **1. SSE stream:** `curl -N http://127.0.0.1/eventstream/clip/v2` stays open >60s (no 1000-iteration cap), receives events
- [ ] **2. Create room:** POST /clip/v2/resource/room → 200, correct rid in response, no duplicates in GET
- [ ] **3. Create entertainment area:** POST /clip/v2/resource/entertainment_configuration → 200, visible in GET immediately
- [ ] **4. Create scene:** POST /clip/v2/resource/scene → 200, actions populated
- [ ] **5. Delete smart_scene:** DELETE /clip/v2/resource/smart_scene/<id> → 200
- [ ] **6. Delete geofence_client:** DELETE /clip/v2/resource/geofence_client/<id> → 200
- [ ] **7. Delete motion:** DELETE /clip/v2/resource/motion/<id> → 405, parent sensor intact
- [ ] **8. Type casing:** room with `"type":"room"` in body → displays as room, not zone
- [ ] **9. behavior_instance without "where":** POST without configuration.where → 200, no crash
- [ ] **10. V1 room create:** POST /api/<user>/groups → still works, events fire
- [ ] **11. Two SSE clients:** both receive all events
- [ ] **12. Restart persistence:** all created resources survive restart

- [ ] Commit: `test: verify V2 event, ID, and type bug fixes`
