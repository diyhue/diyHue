import paho.mqtt.client as mqtt
import json
from functions.colors import hsv_to_rgb


# Mqtt client creation
# You will need to keep this around, because it will manage all the pushed messages
client = mqtt.Client()

# Configuration stuff
discoveryPrefix = "homeassistant"
latestStates = {}
discoveredDevices = {}

# on_connect handler (linked to client below)
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    autodiscoveryTopic = discoveryPrefix + "/light/+/light/config" # + in topic is wildcard
    client.subscribe(autodiscoveryTopic)

# on_message handler (linked to client below)
def on_message(client, userdata, msg):
    if msg.topic.startswith(discoveryPrefix + "/light/"):
        on_autodiscovery_light(msg)
    else:
        on_state_update(msg)

# Will get called zero or more times depending on how many lights are available for autodiscovery
def on_autodiscovery_light(msg):
    data = json.loads(msg.payload)
    print("Auto discovery message on: " + msg.topic)
    print(json.dumps(data, indent=4))
    client.subscribe(data['state_topic'])
    discoveredDevices[data['unique_id']] = data;

def on_state_update(msg):
    print("State message on: " + msg.topic)
    data = json.loads(msg.payload)
    latestStates[msg.topic] = data
    print(json.dumps(data, indent=4))

def set_light(address, light, data):
    state = {}
    colorFromHsv = False
    for key, value in data.items():
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

    if colorFromHsv:
        color = hsv_to_rgb(data['hue'], data['sat'], light["state"]["bri"])
        state['color'] = { 'r': color[0], 'g': color[1], 'b': color[2] }

    message = json.dumps(state);
    print("this is sent on mqtt " + address['command_topic'] + " " + message)
    client.publish(address['command_topic'], message)

def get_light_state(address, light):
    if latestStates[address['state_topic']] is None:
        return { 'reachable': False }
    
    state = { 'reachable': True }
    mqttState = latestStates[address['state_topic']]
    for key, value in mqttState.items():
        if key == "state":
            state['on'] = (value == 'ON')
        if key == "brightness":
            state['bri'] = value
        if key == "color":
            state["colormode"] = "xy"
            state['xy'] = [value['x'], value['y']]

    return state

def mqttServer(config, lights, adresses, sensors):
    # ================= MQTT CLIENT Connection========================
    # Set user/password on client if supplied
    if config["mqttUser"] != "" and config["mqttPassword"] != "":
        client.username_pw_set(config["mqttUser"],config["mqttPassword"])

    if config['discoveryPrefix'] is not None:
        discoveryPrefix = config['discoveryPrefix']

    # Setup handlers
    client.on_connect = on_connect
    client.on_message = on_message
    # Connect to the server
    client.connect(config["mqttServer"], config["mqttPort"])

    # start the loop to keep receiving data
    client.loop_start()
