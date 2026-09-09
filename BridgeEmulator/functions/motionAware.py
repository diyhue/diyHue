import uuid
import configManager
import logManager

from datetime import datetime, timezone
from threading import RLock
from HueObjects import StreamEvent
from functions.core import bridgeIdentity
from motionAwareConfig import (
    CONVENIENCE_AREA_MOTION,
    DEFAULT_AREA_ENABLED,
    DEFAULT_HEALTH,
    DEFAULT_SENSITIVITY,
    DEFAULT_SERVICE_ENABLED,
    MAX_SENSITIVITY,
    MOTION_AREA_CANDIDATE,
    MOTION_AREA_CONFIGURATION,
    MOTION_SERVICE_TYPES,
    SECURITY_AREA_MOTION,
    SERVED_MOTION_RESOURCE_TYPES,
    VALID_GROUP_TYPES,
    get_motion_aware_areas,
    get_stored_area,
    read_bool,
    read_int,
    read_health,
    read_nonempty_string,
    read_participants,
    read_resource_reference,
)


logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config

# Runtime RF state is intentionally process-local. Config persistence stores
# user configuration only; a restart must not resurrect a stale motion event.
_runtime_lock = RLock()
_runtime_motion = {}
_quiet_changed = {}


def _utcTimestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def isMotionAwareAvailable():
    """Capability is a Bridge Pro property, never inferred from data presence."""
    config = bridgeConfig.get("config", {})
    return bridgeIdentity(config)["profile"] == "pro"


def motionAwareStoredAreas():
    """Return persisted MotionAware overrides without mutating config."""
    return get_motion_aware_areas(bridgeConfig.get("config", {}))


def motionAwareStoredArea(area_id):
    return get_stored_area(bridgeConfig.get("config", {}), area_id)


def _storedAreasForWrite():
    return get_motion_aware_areas(bridgeConfig["config"], create=True)


def motionAwareRuntimeState(area_id):
    with _runtime_lock:
        state = _runtime_motion.get(area_id)
        if state is None:
            return None
        motion = bool(state["motion"])
        return {
            "motion": motion,
            "motion_valid": True,
            "motion_report": {
                "changed": state["changed"],
                "motion": motion,
            },
        }


def clearMotionAwareRuntime(area_id):
    with _runtime_lock:
        _runtime_motion.pop(area_id, None)
        _quiet_changed.pop(area_id, None)


def v2MotionAreaCandidateService(device):
    """Return the reference-only MotionAware service for a light device."""
    return {
        "rid": str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            device.id_v2 + "motion_area_candidate"
        )),
        "rtype": MOTION_AREA_CANDIDATE
    }


def devicesForGroup(group):
    """Resolve live light-device members and ignore dangling weakrefs."""
    result = []
    seen = set()
    for reference in getattr(group, "lights", []):
        device = reference() if callable(reference) else reference
        device_id = getattr(device, "id_v2", None)
        if (
            device is None
            or not isinstance(device_id, str)
            or not device_id
            or not hasattr(device, "getDevice")
            or device_id in seen
        ):
            continue
        seen.add(device_id)
        result.append(device)
    result.sort(key=lambda item: item.id_v2)
    return result


def _candidateIsReachable(device):
    """A missing reachability field is legacy-compatible; explicit false is not."""
    try:
        state = device.firstElement().state
    except (AttributeError, IndexError, KeyError, TypeError):
        return True
    return state.get("reachable") is not False


def isMotionAwareCandidateDevice(device):
    """Whether a Pro light exposes the candidate capability service.

    Reachability is dynamic state, not capability.  Keeping the service on an
    unreachable device preserves references for an existing area; the create
    validator still filters unreachable devices via ``motionAwareCandidates``.
    """
    return (
        isMotionAwareAvailable()
        and getattr(device, "group_v1", None) == "lights"
        and hasattr(device, "getDevice")
    )


def motionAwareCandidates(candidate_ids=None):
    """Return every advertised, reachable Pro candidate keyed by candidate RID."""
    if not isMotionAwareAvailable():
        return {}

    wanted = set(candidate_ids or ())
    result = {}
    for device in bridgeConfig.get("device", {}).values():
        if not isMotionAwareCandidateDevice(device):
            continue
        if not _candidateIsReachable(device):
            continue
        candidate = v2MotionAreaCandidateService(device)
        if not wanted or candidate["rid"] in wanted:
            result[candidate["rid"]] = device
    return result


def allMotionAwareCandidates(candidate_ids=None):
    """Resolve candidate services including temporarily unreachable lights.

    This is used only when rendering persisted areas.  A configured area must
    remain visible with participant health ``unhealthy`` while a light is
    offline; otherwise the API would emit dangling references or hide the
    entire area and the Hue client could not recover it after reconnect.
    """
    if not isMotionAwareAvailable():
        return {}
    wanted = set(candidate_ids or ())
    result = {}
    for device in bridgeConfig.get("device", {}).values():
        if not isMotionAwareCandidateDevice(device):
            continue
        candidate = v2MotionAreaCandidateService(device)
        if not wanted or candidate["rid"] in wanted:
            result[candidate["rid"]] = device
    return result


def usedMotionAwareCandidateIds(exclude_area_id=None):
    """Return participant candidate IDs reserved by persisted areas.

    The Hue client receives candidates as device services, while a configured
    area records which of those services it owns.  Keeping that allocation in
    one place prevents two areas from silently claiming the same light.
    Invalid legacy records are ignored here; they are not valid allocations.
    """
    used = set()
    for area_id, area in motionAwareStoredAreas().items():
        if area_id == exclude_area_id or not isinstance(area, dict):
            continue
        participants = read_participants(area.get("participants"))
        if participants is None:
            continue
        used.update(item["resource"]["rid"] for item in participants)
    return used


def _validateCandidateSelection(candidate_ids, exclude_area_id=None):
    """Resolve a 3--4 light selection and reject unreachable/reused IDs."""
    if not isinstance(candidate_ids, list) or not 3 <= len(candidate_ids) <= 4:
        raise ValueError("participants must contain three or four devices")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("participants must be unique")

    candidates = motionAwareCandidates(candidate_ids)
    if len(candidates) != len(candidate_ids):
        raise ValueError("participants must reference eligible candidates")

    reused = set(candidate_ids) & usedMotionAwareCandidateIds(exclude_area_id)
    if reused:
        raise ValueError("participants are already assigned to another MotionAware area")

    return candidates


def v2GroupReference(group):
    """Map an existing diyHue group to the exact V2 reference it exposes."""
    group_type = getattr(group, "type", None)
    if getattr(group, "id_v1", None) == "0":
        return {
            "rid": str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                group.id_v2 + "bridge_home",
            )),
            "rtype": "bridge_home",
        }
    if group_type == "Room":
        return {"rid": group.getV2Room()["id"], "rtype": "room"}
    if group_type == "Zone":
        return {"rid": group.getV2Zone()["id"], "rtype": "zone"}
    return None


def groupForMotionAwareReference(reference):
    """Resolve a stored V2 group reference without creating dangling links."""
    reference = read_resource_reference(reference, VALID_GROUP_TYPES)
    if reference is None:
        return None
    for group in bridgeConfig.get("groups", {}).values():
        if v2GroupReference(group) == reference:
            return group
    return None


def v2MotionAwareRooms():
    """Legacy compatibility helper for old room-derived area identifiers."""
    if not isMotionAwareAvailable():
        return []
    result = []
    for group in bridgeConfig.get("groups", {}).values():
        if getattr(group, "type", None) != "Room":
            continue
        devices = devicesForGroup(group)
        if 3 <= len(devices) <= 4:
            result.append((group, devices))
    result.sort(key=lambda item: item[0].getV2Room()["id"])
    return result


def v2MotionAreaIds(group):
    """Legacy stable IDs retained for pre-subset room-backed areas."""
    room_id = group.getV2Room()["id"]
    area_id = str(uuid.uuid5(
        uuid.NAMESPACE_URL,
        room_id + MOTION_AREA_CONFIGURATION,
    ))
    return v2MotionAreaServiceIds(area_id, area_id)


def v2MotionAreaServiceIds(area_id, legacy_area_id=None):
    """Return stable service IDs for any persisted area ID."""
    legacy_area_id = legacy_area_id or area_id
    convenience_id = str(uuid.uuid5(
        uuid.NAMESPACE_URL,
        legacy_area_id + CONVENIENCE_AREA_MOTION,
    ))
    security_id = str(uuid.uuid5(
        uuid.NAMESPACE_URL,
        legacy_area_id + SECURITY_AREA_MOTION,
    ))
    return area_id, convenience_id, security_id


def newMotionAreaId(group_reference, candidate_ids):
    """Deterministic ID supports multiple areas without random/restart churn."""
    seed = "|".join((
        MOTION_AREA_CONFIGURATION,
        group_reference["rtype"],
        group_reference["rid"],
        *sorted(candidate_ids),
    ))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _legacyGroupForArea(area_id):
    for group, _devices in v2MotionAwareRooms():
        legacy_area_id, _convenience_id, _security_id = v2MotionAreaIds(group)
        if legacy_area_id == area_id:
            return group
    return None


def v2MotionAreaDevices(group, area_id):
    """Use persisted candidate refs; only legacy entries fall back to a room."""
    stored = motionAwareStoredArea(area_id)
    if "participants" in stored:
        participants = read_participants(stored.get("participants"))
        if participants is None or not 3 <= len(participants) <= 4:
            return []
        candidate_ids = [item["resource"]["rid"] for item in participants]
        candidates = allMotionAwareCandidates(candidate_ids)
        if len(candidates) != len(candidate_ids):
            return []
        return [candidates[candidate_id] for candidate_id in candidate_ids]

    # Pre-subset datastore records had no participant list and were tied to
    # one room. Preserve that behavior without treating it as new schema.
    return devicesForGroup(group) if group is not None else []


def v2MotionAreaConfiguration(group, devices, area_id):
    _area_id, convenience_id, security_id = v2MotionAreaServiceIds(area_id)
    stored = motionAwareStoredArea(area_id)
    default_group = v2GroupReference(group)
    group_reference = read_resource_reference(
        stored.get("group"), VALID_GROUP_TYPES
    ) or default_group
    return {
        "id": area_id,
        "name": read_nonempty_string(
            stored,
            "name",
            getattr(group, "name", "Motion area"),
        ),
        "group": group_reference,
        "participants": [
            {
                "resource": v2MotionAreaCandidateService(device),
                "status": {
                    # Reachability is live participant health.  Do not hide
                    # an otherwise valid area while a light is offline.
                    "health": (
                        "healthy"
                        if _candidateIsReachable(device)
                        else "unhealthy"
                    )
                }
            }
            for device in devices
        ],
        "services": [
            {
                "rid": convenience_id,
                "rtype": CONVENIENCE_AREA_MOTION
            },
            {
                "rid": security_id,
                "rtype": SECURITY_AREA_MOTION
            }
        ],
        "health": read_health(stored),
        "enabled": read_bool(stored, "enabled", DEFAULT_AREA_ENABLED),
        "type": MOTION_AREA_CONFIGURATION
    }


def v2MotionAwareSources(group):
    """Return regular diyHue motion sources assigned to a room."""
    result = []

    for member_ref in getattr(group, "sensors", []):
        member = member_ref() if callable(member_ref) else member_ref

        if member is None:
            continue

        if hasattr(member, "getMotion"):
            motion = member.getMotion()

            if motion is not None:
                result.append(member)
                continue

        if getattr(member, "type", None) == "ZLLPresence":
            result.append(member)

    result.sort(
        key=lambda item: getattr(
            item,
            "id_v2",
            getattr(item, "id_v1", "")
        )
    )

    return result


def v2MotionAwareState(group, area_id):
    """Aggregate ordinary room motion sensors into one area state."""
    runtime_state = motionAwareRuntimeState(area_id)
    if runtime_state is not None:
        return runtime_state

    reports = []

    for source in v2MotionAwareSources(group):
        if hasattr(source, "getMotion"):
            resource = source.getMotion()

            if resource is None or not resource.get("enabled", True):
                continue

            motion = resource.get("motion", {})

            if "motion" not in motion:
                continue

            changed = (
                motion.get("motion_report") or {}
            ).get("changed")

            reports.append({
                "motion": bool(motion["motion"]),
                "changed": changed
            })

        elif getattr(source, "type", None) == "ZLLPresence":
            if not source.config.get("on", True):
                continue

            if "presence" not in source.state:
                continue

            reports.append({
                "motion": bool(source.state["presence"]),
                "changed": source.state.get("lastupdated")
            })

    if not reports:
        return {
            "motion": False,
            # A room containing only light participants has no native motion
            # source. Treat the observed quiet state as valid so the stock
            # calibration flow can complete while the area is empty.
            "motion_valid": True,
            # A quiet timestamp is stable until a real transition occurs.
            "motion_report": {
                "changed": _quietChanged(area_id),
                "motion": False
            }
        }

    result = {
        "motion": any(report["motion"] for report in reports),
        "motion_valid": True
    }

    changed = sorted(
        report["changed"]
        for report in reports
        if report["changed"]
        and report["changed"] != "none"
    )

    if changed:
        result["motion_report"] = {
            "changed": changed[-1],
            "motion": result["motion"]
        }

    return result


def _quietChanged(area_id):
    with _runtime_lock:
        changed = _quiet_changed.get(area_id)
        if changed is None:
            changed = _utcTimestamp()
            _quiet_changed[area_id] = changed
        return changed


def v2AreaMotion(group, area_id, resource_id, resource_type):
    stored = (
        motionAwareStoredArea(area_id)
        .get(resource_type, {})
    )

    return {
        "id": resource_id,
        "owner": {
            "rid": area_id,
            "rtype": "motion_area_configuration"
        },
        "enabled": read_bool(stored, "enabled", DEFAULT_SERVICE_ENABLED),
        "motion": v2MotionAwareState(group, area_id),
        "sensitivity": {
            "sensitivity": read_int(
                stored,
                "sensitivity",
                DEFAULT_SENSITIVITY,
                minimum=0,
                maximum=MAX_SENSITIVITY,
            ),
            "sensitivity_max": MAX_SENSITIVITY
        },
        "type": resource_type
    }


def v2MotionAwareResources():
    resources = {
        MOTION_AREA_CONFIGURATION: [],
        CONVENIENCE_AREA_MOTION: [],
        SECURITY_AREA_MOTION: [],
    }

    if not isMotionAwareAvailable():
        return resources

    for area_id, stored_area in sorted(motionAwareStoredAreas().items()):
        if not isinstance(area_id, str) or not isinstance(stored_area, dict):
            continue

        group = groupForMotionAwareReference(stored_area.get("group"))
        if group is None:
            group = _legacyGroupForArea(area_id)
        if group is None:
            logging.warning(
                "Ignoring MotionAware area with unresolved group: %s",
                area_id,
            )
            continue

        devices = v2MotionAreaDevices(group, area_id)
        if not 3 <= len(devices) <= 4:
            logging.warning(
                "Ignoring MotionAware area with unavailable participants: %s",
                area_id,
            )
            continue

        _area_id, convenience_id, security_id = v2MotionAreaServiceIds(area_id)

        resources[MOTION_AREA_CONFIGURATION].append(
            v2MotionAreaConfiguration(group, devices, area_id)
        )

        resources[CONVENIENCE_AREA_MOTION].append(
            v2AreaMotion(
                group,
                area_id,
                convenience_id,
                CONVENIENCE_AREA_MOTION
            )
        )

        resources[SECURITY_AREA_MOTION].append(
            v2AreaMotion(
                group,
                area_id,
                security_id,
                SECURITY_AREA_MOTION
            )
        )

    return resources


def findMotionAwareResource(resource_type, resource_id):
    """Resolve one generated MotionAware resource by V2 id."""
    if resource_type not in SERVED_MOTION_RESOURCE_TYPES:
        return None

    for resource in v2MotionAwareResources()[resource_type]:
        if resource["id"] == resource_id:
            return resource

    return None


def _streamMotionAwareResources(event_type, resources):
    """Publish independently decodable MotionAware resource events."""
    for resource in resources:
        StreamEvent({
            "creationtime": _utcTimestamp(),
            "data": [resource],
            "id": str(uuid.uuid4()),
            "type": event_type,
        })


def createMotionAwareArea(data):
    """Create an area from the candidate references sent by the Hue app."""
    if not isMotionAwareAvailable():
        return None

    if not isinstance(data, dict):
        raise ValueError("POST body must be an object")

    name = data.get("name")
    group_ref = data.get("group")
    participants = data.get("participants")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")

    group_ref = read_resource_reference(group_ref, VALID_GROUP_TYPES)
    if group_ref is None:
        raise ValueError("group must reference a bridge_home, room, or zone")
    if groupForMotionAwareReference(group_ref) is None:
        raise ValueError("group must reference an existing bridge_home, room, or zone")

    if not isinstance(participants, list) or not 3 <= len(participants) <= 4:
        raise ValueError("participants must contain three or four devices")

    candidate_ids = []

    for participant in participants:
        resource = participant.get("resource", {}) if isinstance(participant, dict) else {}

        if (
            resource.get("rtype") != MOTION_AREA_CANDIDATE
            or not isinstance(resource.get("rid"), str)
            or not resource["rid"]
        ):
            raise ValueError("each participant must reference a motion_area_candidate")

        candidate_ids.append(resource["rid"])

    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("participants must be unique")

    # Hue 5.73 permits a subset of three or four reachable candidate lights
    # and permits further areas when they use unused candidates.  Do not
    # reintroduce the obsolete "all lights in one 3--4 device room" rule.
    _validateCandidateSelection(candidate_ids)
    area_id = newMotionAreaId(group_ref, candidate_ids)
    areas = _storedAreasForWrite()
    if area_id in areas:
        raise ValueError("an area with these participants already exists")

    area = {}
    areas[area_id] = area
    area["name"] = name.strip()
    area["group"] = {
        "rid": group_ref["rid"],
        "rtype": group_ref["rtype"]
    }
    if not isinstance(area.get("enabled"), bool):
        area["enabled"] = DEFAULT_AREA_ENABLED
    area["participants"] = [
        {
            "resource": {
                "rid": candidate_id,
                "rtype": MOTION_AREA_CANDIDATE,
            },
            "status": {"health": DEFAULT_HEALTH},
        }
        for candidate_id in candidate_ids
    ]
    # The stock app waits for a healthy area event before leaving the
    # creation screen.  A diyHue-backed room has no hardware calibration
    # phase, so expose the ready state immediately.
    area["health"] = DEFAULT_HEALTH

    configManager.bridgeConfig.save_config(backup=False, resource="config")

    resources = v2MotionAwareResources()
    created = findMotionAwareResource(MOTION_AREA_CONFIGURATION, area_id)
    if created is None:
        # Never persist an area that cannot be represented by the served
        # resource graph.  This is a defensive rollback for legacy/dangling
        # device state discovered between validation and rendering.
        del areas[area_id]
        configManager.bridgeConfig.save_config(backup=False, resource="config")
        raise ValueError("created MotionAware area is not representable")

    event_data = [created]

    for resource_type in MOTION_SERVICE_TYPES:
        event_data.extend(
            item for item in resources[resource_type]
            if item["owner"]["rid"] == area_id
        )

    _streamMotionAwareResources("add", event_data)

    return created


def deleteMotionAwareArea(area_id):
    """Delete a persisted MotionAware area and all generated services."""
    areas = motionAwareStoredAreas()

    if area_id not in areas:
        return False

    _area_id, convenience_id, security_id = v2MotionAreaServiceIds(area_id)
    service_ids = [convenience_id, security_id]
    del areas[area_id]
    configManager.bridgeConfig.save_config(backup=False, resource="config")

    StreamEvent({
        "creationtime": _utcTimestamp(),
        "data": [
            {"id": area_id, "type": MOTION_AREA_CONFIGURATION},
            *[
                {"id": service_id, "type": resource_type}
                for service_id, resource_type in zip(
                    service_ids,
                    MOTION_SERVICE_TYPES
                )
            ]
        ],
        "id": str(uuid.uuid4()),
        "type": "delete"
    })

    clearMotionAwareRuntime(area_id)

    return True


def updateMotionAwareResource(resource_type, resource_id, data):
    """Persist a supported MotionAware V2 PUT and emit its SSE update."""
    if not isMotionAwareAvailable():
        return None

    current = findMotionAwareResource(
        resource_type,
        resource_id
    )

    if current is None:
        return None

    if not isinstance(data, dict):
        raise ValueError("PUT body must be an object")

    if "id" in data and data["id"] != resource_id:
        raise ValueError("id does not match the addressed resource")

    area_id = (
        resource_id
        if resource_type == "motion_area_configuration"
        else current["owner"]["rid"]
    )

    changes = {}

    if resource_type == "motion_area_configuration":
        unsupported = set(data) - {"id", "name", "group", "participants", "enabled"}
        if unsupported:
            raise ValueError("unsupported MotionAware configuration fields")

        if "name" in data:
            if (
                not isinstance(data["name"], str)
                or not data["name"].strip()
            ):
                raise ValueError("name must be a non-empty string")

            changes["name"] = data["name"].strip()

        if "enabled" in data:
            if not isinstance(data["enabled"], bool):
                raise ValueError("enabled must be boolean")

            changes["enabled"] = data["enabled"]

        if "group" in data:
            group = read_resource_reference(data["group"], VALID_GROUP_TYPES)
            if group is None or groupForMotionAwareReference(group) is None:
                raise ValueError("group must reference an existing bridge_home, room, or zone")
            changes["group"] = group

        if "participants" in data:
            participants = read_participants(data["participants"])
            if participants is None or not 3 <= len(participants) <= 4:
                raise ValueError(
                    "participants must contain three or four unique candidates"
                )

            candidate_ids = [
                participant["resource"]["rid"]
                for participant in participants
            ]
            _validateCandidateSelection(candidate_ids, exclude_area_id=area_id)
            changes["participants"] = participants

    else:
        unsupported = set(data) - {"id", "enabled", "sensitivity"}
        if unsupported:
            raise ValueError("unsupported MotionAware service fields")

        if "enabled" in data:
            if not isinstance(data["enabled"], bool):
                raise ValueError("enabled must be boolean")

            changes["enabled"] = data["enabled"]

        if "sensitivity" in data:
            sensitivity = data["sensitivity"]

            if not isinstance(sensitivity, dict):
                raise ValueError(
                    "sensitivity must be an object"
                )

            if "sensitivity" not in sensitivity:
                raise ValueError(
                    "sensitivity.sensitivity is required"
                )

            value = sensitivity["sensitivity"]

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= MAX_SENSITIVITY
            ):
                raise ValueError(
                    "sensitivity must be an integer from 0 to 4"
                )

            changes["sensitivity"] = value

    if not changes:
        return current

    # Do not persist or emit an SSE update when the requested
    # properties already match the generated resource state.
    effective_changes = {}

    for key, value in changes.items():
        if key == "sensitivity":
            current_value = (
                current.get("sensitivity", {})
                .get("sensitivity")
            )
        else:
            current_value = current.get(key)

        if current_value != value:
            effective_changes[key] = value

    changes = effective_changes

    if not changes:
        return current

    areas = _storedAreasForWrite()
    area = areas.setdefault(
        area_id,
        {}
    )
    if not isinstance(area, dict):
        area = {}
        areas[area_id] = area

    if resource_type == "motion_area_configuration":
        area.update(changes)
    else:
        service = area.setdefault(
            resource_type,
            {}
        )
        service.update(changes)

    configManager.bridgeConfig.save_config(
        backup=False,
        resource="config"
    )

    updated = findMotionAwareResource(
        resource_type,
        resource_id
    )

    # Hue's typed MotionAware reducer consumes complete resources. Partial
    # patches can discard owner/services/participants in the cached model.
    event_data = updated

    StreamEvent({
        "creationtime": _utcTimestamp(),
        "data": [event_data],
        "id": str(uuid.uuid4()),
        "type": "update"
    })

    return updated


def setMotionAwareRuntimeMotion(area_id, value, source="runtime"):
    """Set transient motion state and emit only real boolean transitions."""
    if not isMotionAwareAvailable() or area_id not in motionAwareStoredAreas():
        return []
    if not isinstance(value, bool):
        raise ValueError("motion value must be boolean")

    area = motionAwareStoredArea(area_id)
    if area.get("enabled") is False:
        return []
    enabled_services = [
        area.get(resource_type, {}).get("enabled", True)
        if isinstance(area.get(resource_type, {}), dict)
        else True
        for resource_type in MOTION_SERVICE_TYPES
    ]
    if not any(enabled_services):
        return []

    with _runtime_lock:
        current = _runtime_motion.get(area_id)
        if current is not None and current["motion"] == value:
            return []

    before = motionAwareSnapshot()
    with _runtime_lock:
        _runtime_motion[area_id] = {
            "motion": value,
            "changed": _utcTimestamp(),
            "source": str(source),
        }
        _quiet_changed.pop(area_id, None)

    updates = streamMotionAwareTransitions(before)
    # MotionArea behaviors are keyed by the area configuration resource, so
    # dispatch them once per real transition after the V2 event is generated.
    try:
        from functions.behavior_instance import checkMotionAwareBehaviorInstances
        checkMotionAwareBehaviorInstances(area_id, value)
    except Exception as err:
        # A malformed/legacy behavior must not break MotionAware state or SSE.
        logging.warning("MotionAware behavior dispatch failed: %s", err)
    logging.info(
        "MotionAware runtime area=%s motion=%s source=%s updates=%s",
        area_id,
        value,
        source,
        len(updates),
    )
    return updates


def motionAwareSnapshot():
    """Capture transition-relevant MotionAware state."""
    if not isMotionAwareAvailable():
        return {}

    try:
        resources = v2MotionAwareResources()
    except Exception as err:
        logging.warning(
            "Unable to snapshot MotionAware state: %s",
            err
        )
        return {}

    snapshot = {}

    for resource_type in MOTION_SERVICE_TYPES:
        for resource in resources[resource_type]:
            motion = resource.get("motion", {})

            snapshot[(resource_type, resource["id"])] = (
                bool(motion.get("motion", False)),
                bool(motion.get("motion_valid", False)),
            )

    return snapshot


def streamMotionAwareTransitions(before):
    """Emit V2 updates only when aggregate area motion changes."""
    if not before:
        return []

    if not isMotionAwareAvailable():
        return []

    try:
        resources = v2MotionAwareResources()
    except Exception as err:
        logging.warning(
            "Unable to build MotionAware transition: %s",
            err
        )
        return []

    updates = []

    for resource_type in MOTION_SERVICE_TYPES:
        for resource in resources[resource_type]:
            key = (resource_type, resource["id"])

            if key not in before:
                continue

            motion = resource.get("motion", {})

            after = (
                bool(motion.get("motion", False)),
                bool(motion.get("motion_valid", False)),
            )

            if before[key] == after:
                continue

            updates.append(resource)

    if not updates:
        return []

    _streamMotionAwareResources("update", updates)

    return updates
