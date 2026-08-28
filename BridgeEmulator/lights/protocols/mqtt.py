import logManager
import json
import random
import threading
from time import monotonic

import paho.mqtt.publish as publish

from functions.colors import hsv_to_rgb, convert_xy

logging = logManager.logger.get_logger(__name__)

_effect_lock = threading.Lock()
_effect_stop = {}
_effect_base_bri = {}
_effect_recent_frames = {}


def _mqtt_auth(mqtt_cfg):
    if (
        mqtt_cfg["mqttUser"] != ""
        and mqtt_cfg["mqttPassword"] != ""
    ):
        return {
            "username": mqtt_cfg["mqttUser"],
            "password": mqtt_cfg["mqttPassword"],
        }
    return None


def _stop_emulated_effect(topic):
    with _effect_lock:
        stop_event = _effect_stop.pop(topic, None)
        base_bri = _effect_base_bri.pop(topic, None)
        _effect_recent_frames.pop(topic, None)

    if stop_event is not None:
        stop_event.set()

    return base_bri


def _is_emulated_effect_feedback(topic, data):
    """
    Detect Z2M reports caused by our own Candle/Fire frames.

    Keep several recent frames because Zigbee/Z2M acknowledgements
    can arrive after a newer animation frame has already been sent.
    """
    now = monotonic()

    try:
        reported_bri = int(data.get("brightness"))
    except (TypeError, ValueError):
        return False

    with _effect_lock:
        if topic not in _effect_stop:
            return False

        frames = _effect_recent_frames.get(topic, [])

        # Only retain very recent animation commands.
        frames = [
            (bri, sent_at)
            for bri, sent_at in frames
            if now - sent_at <= 4.0
        ]

        matched = any(
            bri == reported_bri
            for bri, sent_at in frames
        )

        _effect_recent_frames[topic] = frames

    return (
        matched
        and data.get("state") == "ON"
    )



def _effect_timing_scale(speed):
    """
    Hue exposes effect speed as 0.0..1.0.
    Preserve our current timing at the Hue default-ish 0.5,
    make 0 slower and 1 faster without turning flicker into strobe.
    """
    try:
        speed = max(0.0, min(1.0, float(speed)))
    except (TypeError, ValueError):
        speed = 0.5

    # 0.0 -> 2.0x timing
    # 0.5 -> 1.0x timing
    # 1.0 -> 0.5x timing
    return 2.0 ** (1.0 - 2.0 * speed)


def _effect_worker(topic, effect, base_bri, speed, mqtt_cfg, stop_event):
    auth = _mqtt_auth(mqtt_cfg)
    timing_scale = _effect_timing_scale(speed)

    # Hue brightness is treated as the reference level, not as
    # a hard upper ceiling. Native effects can visually breathe
    # slightly above and below the selected level.
    level_factor = 1.0

    try:
        while not stop_event.is_set():

            with _effect_lock:
                current_base_bri = _effect_base_bri.get(
                    topic,
                    base_bri
                )

            r = random.random()

            if effect == "candle":
                # Candle:
                # mostly subtle flicker, occasionally a short,
                # clearly visible dip or small flare.
                if r < 0.13:
                    # deeper wick flicker
                    target_factor = random.uniform(0.62, 0.78)

                elif r < 0.21:
                    # little upward flare
                    target_factor = random.uniform(1.01, 1.06)

                else:
                    # normal gentle candle movement
                    target_factor = random.uniform(0.82, 1.03)

                # Only light inertia. The previous version smoothed
                # this too heavily and made the effect look static.
                level_factor = (
                    level_factor * 0.12
                    + target_factor * 0.88
                )

                transition = (
                    random.uniform(0.14, 0.30)
                    * timing_scale
                )

                # Occasionally make two movements arrive closer
                # together, like a short candle flicker.
                if random.random() < 0.20:
                    delay = (
                        random.uniform(0.32, 0.52)
                        * timing_scale
                    )
                else:
                    delay = (
                        random.uniform(0.58, 1.02)
                        * timing_scale
                    )

            elif effect == "fire":
                # Fireplace:
                # more movement and a larger brightness envelope
                # than Candle -- "dancing flames", not a slow pulse.
                if r < 0.18:
                    # noticeable flame dip
                    target_factor = random.uniform(0.54, 0.73)

                elif r < 0.34:
                    # flame-up
                    target_factor = random.uniform(1.02, 1.10)

                else:
                    # normal dancing flame
                    target_factor = random.uniform(0.70, 1.04)

                level_factor = (
                    level_factor * 0.10
                    + target_factor * 0.90
                )

                transition = (
                    random.uniform(0.14, 0.32)
                    * timing_scale
                )

                # Fireplace gets slightly more frequent short
                # movements than Candle, but stays below a rate
                # that would unnecessarily hammer Zigbee.
                if random.random() < 0.28:
                    delay = (
                        random.uniform(0.30, 0.50)
                        * timing_scale
                    )
                else:
                    delay = (
                        random.uniform(0.52, 0.92)
                        * timing_scale
                    )

            else:
                return

            brightness = max(
                1,
                min(
                    254,
                    round(current_base_bri * level_factor)
                )
            )

            payload = {
                "state": "ON",
                "brightness": brightness,
                "transition": transition,
            }

            # OFF may arrive asynchronously from Home Assistant /
            # Zigbee2MQTT. Never publish another effect frame after
            # the stop event has been raised.
            if stop_event.is_set():
                break

            # Remember this exact animation frame so the MQTT state
            # subscriber can distinguish it from a real HA/user
            # brightness change.
            with _effect_lock:
                frames = _effect_recent_frames.setdefault(
                    topic,
                    []
                )

                frames.append(
                    (int(brightness), monotonic())
                )

                # More than enough to cover normal Z2M latency
                # without allowing the list to grow indefinitely.
                if len(frames) > 16:
                    del frames[:-16]

            try:
                publish.single(
                    topic,
                    json.dumps(payload),
                    hostname=mqtt_cfg["mqttServer"],
                    port=mqtt_cfg["mqttPort"],
                    auth=auth,
                )

            except Exception as e:
                logging.warning(
                    "MQTT emulated %s effect failed for %s: %s",
                    effect,
                    topic,
                    e,
                )

            stop_event.wait(delay)

    finally:
        with _effect_lock:
            if _effect_stop.get(topic) is stop_event:
                _effect_stop.pop(topic, None)
                _effect_base_bri.pop(topic, None)
                _effect_recent_frames.pop(topic, None)



def _start_emulated_effect(topic, effect, base_bri, speed, mqtt_cfg):
    _stop_emulated_effect(topic)

    stop_event = threading.Event()

    with _effect_lock:
        _effect_stop[topic] = stop_event
        _effect_base_bri[topic] = base_bri

    threading.Thread(
        target=_effect_worker,
        args=(topic, effect, base_bri, speed, mqtt_cfg, stop_event),
        name="diyHue-%s-%s" % (effect, topic),
        daemon=True,
    ).start()


def set_light(light, data):
    messages = []
    lightsData = {}

    if "lights" not in data:
        lightsData = {
            light.protocol_cfg["command_topic"]: data
        }
    else:
        lightsData = data["lights"]

    mqtt_cfg = light.protocol_cfg["mqtt_server"]
    auth = _mqtt_auth(mqtt_cfg)

    effects_to_start = []

    for topic in lightsData.keys():
        command = lightsData[topic]
        payload = {"transition": 0.3}
        colorFromHsv = False

        effect = command.get("effect")

        try:
            effect_speed = max(
                0.0,
                min(
                    1.0,
                    float(command.get("effect_speed", 0.5))
                )
            )
        except (TypeError, ValueError):
            effect_speed = 0.5

        emulate_z2m = topic.startswith("zigbee2mqtt/")

        old_base_bri = None

        if effect in ("candle", "fire") and emulate_z2m:
            old_base_bri = _stop_emulated_effect(topic)

        elif effect == "no_effect" and emulate_z2m:
            old_base_bri = _stop_emulated_effect(topic)

        elif effect is not None:
            old_base_bri = _stop_emulated_effect(topic)

        # OFF really stops the running effect.
        elif command.get("on") is False:
            _stop_emulated_effect(topic)

        # Colour/CT changes do NOT stop a running Hue effect.
        # Native Hue allows changing the effect colour while
        # Candle/Fire remains active. The payload below will update
        # the physical colour while the effect worker keeps running.

        # Hue can send brightness updates while an effect remains
        # active. Update the effect level instead of stopping it.
        elif "bri" in command:
            try:
                new_base_bri = max(
                    1,
                    min(254, int(command["bri"]))
                )
            except (TypeError, ValueError):
                new_base_bri = None

            if new_base_bri is not None:
                with _effect_lock:
                    if topic in _effect_base_bri:
                        _effect_base_bri[topic] = new_base_bri

        # Deliberately do nothing for on=True.
        # Hue sends harmless ON refreshes while effects are active.

        for key, value in command.items():

            if key == "on":
                payload["state"] = "ON" if value is True else "OFF"

            if key == "bri":
                payload["brightness"] = value

            if key == "xy":
                payload["color"] = {
                    "x": value[0],
                    "y": value[1],
                }

            if key == "gradient":
                rgbs = list(
                    map(
                        lambda xy_record: convert_xy(
                            xy_record["color"]["xy"]["x"],
                            xy_record["color"]["xy"]["y"],
                            255,
                        ),
                        value["points"],
                    )
                )

                hexes = list(
                    map(
                        lambda rgb:
                            "#"
                            + format(int(round(rgb[0])), "02x")
                            + format(int(round(rgb[1])), "02x")
                            + format(int(round(rgb[2])), "02x"),
                        rgbs,
                    )
                )

                hexes.reverse()
                payload["gradient"] = hexes

            if key == "ct":
                payload["color_temp"] = value

            if key == "hue" or key == "sat":
                colorFromHsv = True

            if key == "alert" and value != "none":
                payload["alert"] = value

            if key == "transitiontime":
                payload["transition"] = value / 10

            if key == "effect":

                if emulate_z2m and value in ("candle", "fire"):
                    pass

                elif emulate_z2m and value == "no_effect":
                    payload["effect"] = "stop_colorloop"

                else:
                    payload["effect"] = value

        if colorFromHsv:
            hue = command.get(
                "hue",
                light.state.get("hue", 0)
            )

            sat = command.get(
                "sat",
                light.state.get("sat", 0)
            )

            bri = command.get(
                "bri",
                light.state.get("bri", 254)
            )

            color = hsv_to_rgb(hue, sat, bri)

            payload["color"] = {
                "r": color[0],
                "g": color[1],
                "b": color[2],
            }

        if effect == "no_effect" and old_base_bri is not None:
            if "brightness" not in payload:
                payload["brightness"] = old_base_bri

        if len(payload) > 1:
            messages.append({
                "topic": topic,
                "payload": json.dumps(payload),
            })

        if effect in ("candle", "fire") and emulate_z2m:
            base_bri = command.get(
                "bri",
                light.state.get("bri", 160)
            )

            if base_bri is None:
                base_bri = 160

            base_bri = max(
                1,
                min(254, int(base_bri))
            )

            effects_to_start.append(
                (topic, effect, base_bri, effect_speed)
            )

    logging.debug(
        "MQTT publish to: " + json.dumps(messages)
    )

    if messages:
        publish.multiple(
            messages,
            hostname=mqtt_cfg["mqttServer"],
            port=mqtt_cfg["mqttPort"],
            auth=auth,
        )

    for topic, effect, base_bri, effect_speed in effects_to_start:
        logging.info(
            "Starting emulated Hue %s effect for %s at speed %.2f",
            effect,
            topic,
            effect_speed,
        )

        _start_emulated_effect(
            topic,
            effect,
            base_bri,
            effect_speed,
            mqtt_cfg,
        )


def get_light_state(light):
    return {}


def discover(mqtt_config):
    if mqtt_config["enabled"]:
        logging.info("MQTT discovery called")

        auth = _mqtt_auth(mqtt_config)

        try:
            publish.single(
                "zigbee2mqtt/bridge/request/permit_join",
                json.dumps({
                    "value": True,
                    "time": 120,
                }),
                hostname=mqtt_config["mqttServer"],
                port=mqtt_config["mqttPort"],
                auth=auth,
            )

            publish.single(
                "zigbee2mqtt/bridge/config/devices/get",
                hostname=mqtt_config["mqttServer"],
                port=mqtt_config["mqttPort"],
                auth=auth,
            )

        except Exception as e:
            print (str(e))
