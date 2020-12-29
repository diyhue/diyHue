import json
import logging
import random

# External libraries
import paho.mqtt.client as mqtt
import ssl

# internal functions
from functions import light_types, nextFreeId
from functions.colors import hsv_to_rgb

# Mqtt client creation
# You will need to keep this around, because it will manage all the pushed messages
client = mqtt.Client()

# Configuration stuff
discoveryPrefix = "homeassistant"
latestStates = {}
latestAvail = {}
discoveredDevices = {}

# on_connect handler (linked to client below)
def on_connect(client, userdata, flags, rc):
    logging.info("MQTT: Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # Start autodetection on lights
    autodiscoveryTopic = discoveryPrefix + "/light/+/light/config" # + in topic is wildcard
    client.subscribe(autodiscoveryTopic)
    # and plugs too
    autodiscoveryTopic = discoveryPrefix + "/switch/+/switch/config" # + in topic is wildcard
    client.subscribe(autodiscoveryTopic)

# on_message handler (linked to client below)
def on_message(client, userdata, msg):
    if msg.topic.startswith(discoveryPrefix):
        on_autodiscovery_light(msg)
    elif msg.topic == 'zigbee2mqtt/bridge/state' or  msg.topic.endswith("/availability"):
        on_avail_update(msg)
    else:
        on_state_update(msg)

# Will get called zero or more times depending on how many lights are available for autodiscovery
def on_autodiscovery_light(msg):
    data = json.loads(msg.payload)
    logging.info("MQTT: Auto discovery message on: " + msg.topic)
    logging.debug(json.dumps(data, indent=4))
    client.subscribe(data['state_topic'])
    discoveredDevices[data['unique_id']] = data;
    # avail topics
    for availtopic in data['availability']:
        if 'topic' in availtopic:
            logging.info('subscribe avail topic ' + availtopic['topic'])
            client.subscribe(availtopic['topic'])

def on_avail_update(msg):
    data = msg.payload
    logging.info("MQTT: got avail message on " + msg.topic + " = " + str(data.decode("utf-8")))
    latestAvail[msg.topic] = data.decode("utf-8") 

def on_state_update(msg):
    logging.info("MQTT: got state message on " + msg.topic)
    data = json.loads(msg.payload)
    latestStates[msg.topic] = data
    logging.debug(json.dumps(data, indent=4))

def set_light(address, light, data):
    state = {"transition": 0.3}
    colorFromHsv = False
    for key, value in data.items():
        if key == "ct":
            state['color_temp'] = value
        if key == "on":
            state['state'] = "ON" if value == True else "OFF"
        if key == "bri":
            state['brightness'] = value
        if key == "xy":
            state['color'] = {'x': value[0], 'y': value[1]}
        if key == "hue" or key == "sat":
            colorFromHsv = True
        if key == "alert":
            state['alert'] = value
        if key == "transitiontime":
            state['transition'] = value / 10

    if colorFromHsv:
        color = hsv_to_rgb(data['hue'], data['sat'], light["state"]["bri"])
        state['color'] = { 'r': color[0], 'g': color[1], 'b': color[2] }

    message = json.dumps(state);
    logging.debug("MQTT: publish to " + address['command_topic'] + " " + message)
    client.publish(address['command_topic'], message)

def get_light_state(address, light):

    # bridge avail?
    if 'zigbee2mqtt/bridge/state' in latestAvail:
        if latestAvail['zigbee2mqtt/bridge/state'] == "offline":
            # lightRequest.py overwrites reachable - so raise exeception instead
            raise Exception("bridge not avail.")
            return { 'reachable': False }

    # device avail?
    if address['state_topic']+'/availability' in latestAvail:
        if latestAvail[address['state_topic']+'/availability'] == "offline":
            # lightRequest.py overwrites reachable - so raise exeception instead
            raise Exception("device " + address['state_topic'] + " not avail.")
            return { 'reachable': False }

    if address['state_topic'] not in latestStates:
        # lightRequest.py overwrites reachable - so raise exeception instead
        raise Exception("device " + address['state_topic'] + " state not set yet.")
        return { 'reachable': False }

    if latestStates[address['state_topic']] is None:
        # lightRequest.py overwrites reachable - so raise exeception instead
        raise Exception("device " + address['state_topic'] + " state is None!?")
        return { 'reachable': False }
    
    state = { 'reachable': True }
    mqttState = latestStates[address['state_topic']]
    for key, value in mqttState.items():
        if key == "state":
            state['on'] = (value == 'ON')
        if key == "brightness":
            state['bri'] = value
        if key == "color_temp":
            state['ct'] = value
        if key == "color":
            state["colormode"] = "xy"
            state['xy'] = [value['x'], value['y']]

    return state

def discover(bridge_config, new_lights):
    logging.info("MQTT: discovery called")
    for key, data in discoveredDevices.items():
        device_new = True
        for lightkey in bridge_config["lights_address"].keys():
            if bridge_config["lights_address"][lightkey]["protocol"] == "mqtt" and bridge_config["lights_address"][lightkey]["uid"] == key:
                device_new = False
                bridge_config["lights_address"][lightkey]["command_topic"] = data["command_topic"]
                bridge_config["lights_address"][lightkey]["state_topic"] = data["state_topic"]
                break
        
        if device_new:
            light_name = data["device"]["name"] if data["device"]["name"] is not None else data["name"]
            logging.debug("MQTT: Adding light " + light_name)
            new_light_id = nextFreeId(bridge_config, "lights")

            # Device capabilities
            keys = data.keys()
            light_color = "xy" in keys and data["xy"] == True
            light_brightness = "brightness" in keys and data["brightness"] == True
            light_ct = "color_temp" in keys and data["color_temp"] == True

            modelid = None
            if light_color and light_ct:
                modelid = "LCT015"
            elif light_color: # Every light as LCT001? Or also support other lights
                modelid = "LCT001"
            elif light_brightness:
                modelid = "LWB010"
            elif light_ct:
                modelid = "LTW001"
            else:
                # OSRAM Smart+ plug
                modelid = "Plug 01"
       
            # Handle Philips manufacturer a little bit more precise
            # you might look here: https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/devices.js
            if data["device"]["manufacturer"] == 'Philips':
                if data["device"]["model"].find('915005106701') >= 0:
                    # Hue white and color ambiance LightStrip plus
                    modelid = 'LST002'
                if data["device"]["model"].find('7299355PH') >= 0:
                    # Hue white and color ambiance LightStrip 
                    modelid = 'LST001'
                if data["device"]["model"].find('9290018187B') >= 0:
                    # Hue white and color ambiance LightStrip outdoor 
                    modelid = 'LST003'
                if data["device"]["model"].find('8718699703424') >= 0:
                    # Hue white and color ambiance LightStrip plus
                    modelid = 'LCL001'
                if data["device"]["model"].find('9290022890') >= 0:
                    # Hue white and color ambiance LightStrip outdoor 2m 
                    modelid = 'LCL002'

            # Create the light with data from auto discovery
            bridge_config["lights"][new_light_id] = { "name": light_name, "uniqueid": "4a:e0:ad:7f:cf:" + str(random.randrange(0, 99)) + "-1" }
            bridge_config["lights"][new_light_id]["manufacturername"] = data["device"]["manufacturer"]
            bridge_config["lights"][new_light_id]["modelid"] = modelid
            bridge_config["lights"][new_light_id]["productname"] = data["device"]["model"]
            bridge_config["lights"][new_light_id]["swversion"] = data["device"]["sw_version"]
            
            # Set the type, a default state and possibly a light config
            bridge_config["lights"][new_light_id]["type"] = light_types[modelid]["type"]
            bridge_config["lights"][new_light_id]["state"] = light_types[modelid]["state"]
            if "config" in light_types[modelid]:
                bridge_config["lights"][new_light_id]["config"] = light_types[modelid]["config"]
            else:
                bridge_config["lights"][new_light_id]["config"] = {}
            # Add the lights to new lights, so it shows up in the search screen
            new_lights.update({new_light_id: {"name": light_name}})
            
            # Save the mqtt parameters
            bridge_config["lights_address"][new_light_id] = { "protocol": "mqtt", "uid": data["unique_id"], "ip":"none" }
            bridge_config["lights_address"][new_light_id]["state_topic"] = data["state_topic"]
            bridge_config["lights_address"][new_light_id]["command_topic"] = data["command_topic"]


def mqttServer(config, lights, adresses, sensors):
    # ================= MQTT CLIENT Connection========================
    # Set user/password on client if supplied
    if config["mqttUser"] != "" and config["mqttPassword"] != "":
        client.username_pw_set(config["mqttUser"],config["mqttPassword"])

    if config['discoveryPrefix'] is not None:
        discoveryPrefix = config['discoveryPrefix']

    # defaults for TLS and certs 
    if 'mqttCaCerts' not in config:
        config["mqttCaCerts"] = None
    if 'mqttCertfile' not in config:
        config["mqttCertfile"] = None
    if 'mqttKeyfile' not in config:
        config["mqttKeyfile"] = None
    if 'mqttTls' not in config:
        config["mqttTls"] = False
    if 'mqttTlsInsecure' not in config:
        config["mqttTlsInsecure"] = False
    # TLS set? 
    if config["mqttTls"]:
        mqttTlsVersion = ssl.PROTOCOL_TLS
        client.tls_set(ca_certs=config["mqttCaCerts"], certfile=config["mqttCertfile"], keyfile=config["mqttKeyfile"], tls_version=mqttTlsVersion)
        # allow insecure
        if config["mqttTlsInsecure"]:
            client.tls_insecure_set(config["mqttTlsInsecure"])

    # Setup handlers
    client.on_connect = on_connect
    client.on_message = on_message
    # Connect to the server
    client.connect(config["mqttServer"], config["mqttPort"])

    # start the loop to keep receiving data
    client.loop_start()

