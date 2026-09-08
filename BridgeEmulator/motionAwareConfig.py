"""Canonical MotionAware configuration keys and safe readers.

The persisted representation intentionally lives below ``config.motion_aware``.
Live RF/motion state is not part of this schema and must never be written here.
This module has no dependency on the runtime object graph, which makes it safe
to use while config.yaml is being loaded and migrated.
"""

MOTION_AWARE_KEY = "motion_aware"
LEGACY_MOTION_AWARE_KEYS = ("motionAware", "motionaware")
AREAS_KEY = "areas"

MOTION_AREA_CONFIGURATION = "motion_area_configuration"
CONVENIENCE_AREA_MOTION = "convenience_area_motion"
SECURITY_AREA_MOTION = "security_area_motion"
MOTION_AREA_CANDIDATE = "motion_area_candidate"

MOTION_SERVICE_TYPES = (
    CONVENIENCE_AREA_MOTION,
    SECURITY_AREA_MOTION,
)
SERVED_MOTION_RESOURCE_TYPES = (
    MOTION_AREA_CONFIGURATION,
    *MOTION_SERVICE_TYPES,
)

DEFAULT_AREA_ENABLED = True
DEFAULT_SERVICE_ENABLED = True
DEFAULT_SENSITIVITY = 2
MAX_SENSITIVITY = 4
DEFAULT_HEALTH = "healthy"
VALID_HEALTH = ("healthy", "unhealthy")
VALID_GROUP_TYPES = ("bridge_home", "room", "zone")


def normalize_motion_aware_config(config):
    """Normalize only the MotionAware container and return ``(changed, issues)``.

    A missing key remains missing. This is important: config presence is not a
    capability flag. MotionAware availability is derived separately from the
    bridge profile. Unknown fields are retained for forward compatibility.
    Malformed container values are replaced with an empty, inert area map.
    """
    if not isinstance(config, dict):
        raise TypeError("bridge config must be a dictionary")

    changed = False
    issues = []

    # Older experimental builds used camel-case container names.  Migrate
    # them once into the canonical diyHue key instead of silently stranding
    # persisted areas or reading two competing sources of truth.
    legacy_values = [
        config[key]
        for key in LEGACY_MOTION_AWARE_KEYS
        if key in config
    ]
    if MOTION_AWARE_KEY not in config and legacy_values:
        config[MOTION_AWARE_KEY] = legacy_values[0]
        changed = True
    for key in LEGACY_MOTION_AWARE_KEYS:
        if key in config:
            del config[key]
            changed = True
            if len(legacy_values) > 1:
                issues.append("multiple legacy MotionAware keys; first value retained")

    if MOTION_AWARE_KEY not in config:
        return changed, issues

    motion_aware = config.get(MOTION_AWARE_KEY)

    if not isinstance(motion_aware, dict):
        config[MOTION_AWARE_KEY] = {AREAS_KEY: {}}
        return True, ["motion_aware must be an object; reset to an empty area map"]

    if AREAS_KEY not in motion_aware:
        motion_aware[AREAS_KEY] = {}
        changed = True
    elif not isinstance(motion_aware[AREAS_KEY], dict):
        motion_aware[AREAS_KEY] = {}
        changed = True
        issues.append("motion_aware.areas must be an object; reset to empty")

    return changed, issues


def get_motion_aware_areas(config, create=False):
    """Return the canonical area map without leaking malformed containers."""
    if not isinstance(config, dict):
        return {}

    motion_aware = config.get(MOTION_AWARE_KEY)
    if not isinstance(motion_aware, dict):
        if not create:
            return {}
        motion_aware = {}
        config[MOTION_AWARE_KEY] = motion_aware

    areas = motion_aware.get(AREAS_KEY)
    if not isinstance(areas, dict):
        if not create:
            return {}
        areas = {}
        motion_aware[AREAS_KEY] = areas

    return areas


def get_stored_area(config, area_id):
    """Return one valid stored area object or an empty read-only fallback."""
    area = get_motion_aware_areas(config).get(area_id)
    return area if isinstance(area, dict) else {}


def read_bool(mapping, key, default):
    """Read a real JSON boolean, preserving ``False`` and rejecting 0/1."""
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    return value if isinstance(value, bool) else default


def read_int(mapping, key, default, minimum=None, maximum=None):
    """Read an integer without accepting bool (a Python int subclass)."""
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    if minimum is not None and value < minimum:
        return default
    if maximum is not None and value > maximum:
        return default
    return value


def read_nonempty_string(mapping, key, default):
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    return value if isinstance(value, str) and value.strip() else default


def read_health(mapping, key="health", default=DEFAULT_HEALTH):
    """Read the two health enum values understood by Hue's MotionArea model."""
    if not isinstance(mapping, dict):
        return default
    value = mapping.get(key)
    return value if value in VALID_HEALTH else default


def read_resource_reference(value, allowed_types):
    """Return a normalized V2 resource reference or ``None``."""
    if not isinstance(value, dict):
        return None
    rid = value.get("rid")
    rtype = value.get("rtype")
    if not isinstance(rid, str) or not rid or rtype not in allowed_types:
        return None
    return {"rid": rid, "rtype": rtype}


def read_participants(value):
    """Return canonical participant records, or ``None`` if malformed.

    Participant health is server-owned runtime metadata. Persisted legacy
    health is accepted only when it is a non-empty string; otherwise the
    canonical default is used.
    """
    if not isinstance(value, list):
        return None

    result = []
    seen = set()
    for participant in value:
        if not isinstance(participant, dict):
            return None
        resource = read_resource_reference(
            participant.get("resource"),
            (MOTION_AREA_CANDIDATE,),
        )
        if resource is None or resource["rid"] in seen:
            return None
        seen.add(resource["rid"])
        status = participant.get("status")
        health = read_health(status)
        result.append({
            "resource": resource,
            "status": {"health": health},
        })

    return result
