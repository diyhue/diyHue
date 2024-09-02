import logManager
import json

# External
import paho.mqtt.publish as publish

# internal functions
from functions.colors import hsv_to_rgb, convert_xy

logging = logManager.logger.get_logger(__name__)


def set_light(light, data):
    messages = []
    lightsData = {}

    if "lights" not in data:
        lightsData = {light.protocol_cfg["command_topic"]: data}
    else:
        lightsData = data["lights"]

    for topic in lightsData.keys():
        payload = {"transition": 0.3}
        colorFromHsv = False
        for key, value in lightsData[topic].items():
            if key == "on":
                payload['state'] = "ON" if value == True else "OFF"
            if key == "bri":
                payload['brightness'] = value
            if key == "xy":
                payload['color'] = {'x': value[0], 'y': value[1]}
            if key == "gradient":
                rgbs = list(map(lambda xy_record: convert_xy(xy_record['color']['xy']['x'], xy_record['color']['xy']['y'], 255), value['points']))
                hexes = list(map(lambda rgb: 
                    "#" + format(int(round(rgb[0])), '02x') + format(int(round(rgb[1])), '02x') + format(int(round(rgb[2])), '02x'),
                    rgbs))
                hexes.reverse()
                payload['gradient'] = hexes
            if key == "ct":
                payload["color_temp"] = value
            if key == "hue" or key == "sat":
                colorFromHsv = True
            if key == "alert" and value != "none":
                payload['alert'] = value
            if key == "transitiontime":
                payload['transition'] = value / 10
        if colorFromHsv:
            color = hsv_to_rgb(data['hue'], data['sat'], light.state["bri"])
            payload['color'] = { 'r': color[0], 'g': color[1], 'b': color[2] }
        messages.append({"topic": topic, "payload": json.dumps(payload)})
    logging.debug("MQTT publish to: " + json.dumps(messages))
    auth = None
    if light.protocol_cfg["mqtt_server"]["mqttUser"] != "" and light.protocol_cfg["mqtt_server"]["mqttPassword"] != "":
        auth = {'username':  light.protocol_cfg["mqtt_server"]["mqttUser"], 'password':  light.protocol_cfg["mqtt_server"]["mqttPassword"]}
    publish.multiple(messages, hostname= light.protocol_cfg["mqtt_server"]["mqttServer"], port= light.protocol_cfg["mqtt_server"]["mqttPort"], auth=auth)

def get_light_state(light):
    return {}

def discover(mqtt_config):
    if mqtt_config["enabled"]:
        logging.info("MQTT discovery called")
        auth = None
        if mqtt_config["mqttUser"] != "" and mqtt_config["mqttPassword"] != "":
            auth = {'username': mqtt_config["mqttUser"], 'password': mqtt_config["mqttPassword"]}
        try:
            publish.single("zigbee2mqtt/bridge/request/permit_join", json.dumps({"value": True, "time": 120}), hostname=mqtt_config["mqttServer"], port=mqtt_config["mqttPort"], auth=auth)
            publish.single("zigbee2mqtt/bridge/config/devices/get", hostname=mqtt_config["mqttServer"], port=mqtt_config["mqttPort"], auth=auth)
        except Exception as e:
            print (str(e))
