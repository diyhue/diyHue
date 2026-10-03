"""Light state restoration after a Hue Entertainment stream ends."""

from copy import deepcopy
import uuid

import logManager
from lights.light_types import lightTypes

logging = logManager.logger.get_logger(__name__)

STOP_SCRIPT_ID = "7719b841-6b3d-448d-a0e7-601ae9edb6a2"

# Shared Hue preset identifiers. Colour/brightness values come from the
# observed Hue gallery presets, not a documented after-streaming recipe API:
# https://gist.github.com/Hypfer/a0a8b5b9429831a7306ec4300077eaaa
# Temperature-only lights use approximate white-temperature equivalents.
RECIPES = {
    "732ff1d9-76a7-4630-aad0-c8acc499bb0b": {
        "name": "Bright", "bri": 254, "xy": [0.4596, 0.4105], "ct": 366},
    "8c74b9ba-6e89-4083-a2a7-b10a1e566fed": {
        "name": "Dimmed", "bri": 77, "xy": [0.4596, 0.4105], "ct": 366},
    "28bbfeff-1a0c-444e-bb4b-0b74b88e0c95": {
        "name": "Nightlight", "bri": 1, "xy": [0.5610, 0.4042], "ct": 454},
    "a1f7da49-d181-4328-abea-68c9dc4b5416": {
        "name": "Relax", "bri": 143, "xy": [0.5019, 0.4152], "ct": 454},
    "e101a77f-9984-4f61-aac8-15741983c656": {
        "name": "Read", "bri": 254, "xy": [0.4450, 0.4067], "ct": 346},
    "b90c8900-a6b7-422c-a5d3-e170187dbf8c": {
        "name": "Concentrate", "bri": 254, "xy": [0.3691, 0.3719], "ct": 233},
    "7fd2ccc5-5749-4142-b7a5-66405a676f03": {
        "name": "Energize", "bri": 254, "xy": [0.3143, 0.3301], "ct": 156},
}

_RESTORABLE_KEYS = (
    "on", "bri", "colormode", "xy", "ct", "hue", "sat", "gradient", "effect",
)


def snapshot_lights(group):
    """Copy each light before streaming can overwrite its ordinary state.

    The caller owns this snapshot; it must not be persisted in group.stream.
    """
    snapshots = {}
    for light_ref in list(group.lights):
        light = light_ref()
        if light is not None:
            snapshots[light.id_v1] = {
                "id_v2": light.id_v2,
                "state": deepcopy(light.state),
                "effect": light.effect,
            }
    return snapshots


def _stop_configuration(group, bridge_config):
    area_id = str(uuid.uuid5(
        uuid.NAMESPACE_URL, group.id_v2 + "entertainment_configuration"))
    for behavior in list(bridge_config.get("behavior_instance", {}).values()):
        if not behavior.enabled or behavior.script_id != STOP_SCRIPT_ID:
            continue
        configuration = deepcopy(behavior.configuration)
        for location in configuration.get("where", []):
            target = location.get("group", {})
            if (target.get("rid") == area_id
                    and target.get("rtype") == "entertainment_configuration"):
                return configuration
    return None


def _saved_command(state):
    # Changing brightness/colour on some backends implicitly turns a light on.
    # An initially off light only needs an explicit OFF command.
    if not state.get("on", False):
        return {"on": False}
    command = {"on": True}
    for key in ("bri", "effect"):
        if key in state:
            command[key] = deepcopy(state[key])
    mode = state.get("colormode")
    if mode == "xy" and state.get("gradient", {}).get("points"):
        command["gradient"] = deepcopy(state["gradient"])
    elif mode == "xy" and "xy" in state:
        command["xy"] = list(state["xy"])
    elif mode == "ct" and "ct" in state:
        command["ct"] = state["ct"]
    elif mode == "hs":
        for key in ("hue", "sat"):
            if key in state:
                command[key] = state[key]
    return command


def _recipe_command(light, recipe):
    # Streaming adds xy even to temperature-only lights. Use model capabilities,
    # rather than the modified streaming state, to choose the command format.
    model = lightTypes.get(light.modelid, {})
    capabilities = model.get("state", light.state)
    command = {"on": True}
    if "bri" in capabilities:
        command["bri"] = recipe["bri"]
    if "xy" in capabilities:
        command["xy"] = list(recipe["xy"])
        if "gradient" in capabilities:
            # Replace a previous multicolour gradient with a uniform preset.
            count = len(light.state.get("gradient", {}).get("points", [])) or 3
            command["gradient"] = {"points": [
                {"color": {"xy": {"x": recipe["xy"][0],
                                  "y": recipe["xy"][1]}}}
                for _ in range(count)
            ]}
    elif "ct" in capabilities:
        limits = model.get("v1_static", {}).get("capabilities", {}).get(
            "control", {}).get("ct", {})
        command["ct"] = max(limits.get("min", 153), min(
            limits.get("max", 500), recipe["ct"]))
    if "effect" in capabilities:
        command["effect"] = "no_effect" if light.protocol == "wled" else "none"
    return command


def apply_stop_preference(group, bridge_config, snapshots):
    """Apply the enabled preference for this area through normal light drivers.

    Call only after the stream/relay has stopped and mode is homeautomation.
    Pause (do_nothing), no preference, unsupported choices and unknown recipe
    IDs keep the current output unchanged.
    """
    configuration = _stop_configuration(group, bridge_config)
    if configuration is None:
        return
    end_state = configuration.get("end_state")
    if end_state == "do_nothing":
        logging.info("Keeping the last streaming light state for %s", group.name)
        return
    recipe = None
    # The app can leave a stale end_scene behind when selecting off/last_state.
    # Only consult that reference if end_state actually requests a scene.
    if end_state == "scene":
        target = configuration.get("end_scene", {})
        if target.get("rtype") == "recipe":
            recipe = RECIPES.get(target.get("rid"))
        if recipe is None:
            logging.warning("Unsupported after-streaming target: %s", target)
            return
    elif end_state not in ("off", "last_state"):
        logging.info("Leaving lights unchanged for after-streaming state %r",
                     end_state)
        return

    logging.info("Applying after-streaming preference %s to %s",
                 recipe["name"] if recipe else end_state, group.name)
    for light_ref in list(group.lights):
        light = light_ref()
        if light is None:
            continue
        try:
            if end_state == "off":
                command = {"on": False}
            elif end_state == "last_state":
                saved = snapshots.get(light.id_v1)
                # A light removed/replaced during the stream has no valid snapshot.
                if saved is None or saved["id_v2"] != light.id_v2:
                    continue
                state = saved["state"]
                light.state.update({key: deepcopy(state[key])
                                    for key in _RESTORABLE_KEYS if key in state})
                light.effect = saved["effect"]
                command = _saved_command(state)
            else:
                command = _recipe_command(light, recipe)
                light.effect = "no_effect"
            # Native multi-light and MQTT drivers both accept an individual
            # command. In particular, do not skip OFF lights that have a bri.
            light.setV1State(command, advertise=False)
        except Exception:
            logging.exception("Could not restore light %s after streaming",
                              light.id_v1)
