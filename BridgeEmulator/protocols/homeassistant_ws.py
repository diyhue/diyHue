import json
import logging
import time
import random
import threading

from ws4py.client.threadedclient import WebSocketClient
from functions import light_types, nextFreeId
from functions.colors import hsv_to_rgb

discovery_timeout_seconds = 60
discovery_result = threading.Event()
next_connection_error_log = 0
logging_backoff = 2 # 2 Second back off
homeassistant_token = ''
homeassistant_url = 'ws://127.0.0.1:8123/api/websocket'
homeassistant_ws_client = None
include_by_default = False

# This is Home Assistant States so looks like this:
# {
#   'entity_id': 'light.my_light',
#   'state': 'on',
#   'attributes': {
#        'min_mireds': 153, 
#        'max_mireds': 500,
#        'effect_list': ['colorloop', 'random'],
#        'brightness': 254, 
#        'hs_color': [291.687, 65.098], 
#        'rgb_color': [232, 89, 255], 
#        'xy_color': [0.348, 0.168], 
#        'is_hue_group': True, 
#        'friendly_name': 'My Light', 
#        'supported_features': 63
#   },
#   'last_changed': '2019-01-09T10:35:39.148462+00:00',
#    'last_updated': '2019-01-09T10:35:39.148462+00:00', 
#    'context': {'id': 'X', 'parent_id': None, 'user_id': None}
# }
latest_states = {}

class HomeAssistantClient(WebSocketClient):

    message_id = 1
    id_to_type = {}

    def opened(self):
        logging.info("Home Assistant WebSocket Connection Opened")

    def closed(self, code, reason=None):
        logging.info("Home Assistant WebSocket Connection Closed. Code: {} Reason {}".format(code, reason))
        for home_assistant_state in latest_states.values():
            if 'state' in home_assistant_state:
                home_assistant_state['state'] = 'unavailable'

    def received_message(self, m):
        # logging.debug("Received message: {}".format(m))
        message_text = m.data.decode(m.encoding)
        message = json.loads(message_text)
        if message.get('type', None) == "auth_required":
            self.do_auth_required(message)
        elif message.get('type', None) == "auth_ok":
            self.do_auth_complete()
        elif message.get('type', None) == "auth_invalid":
            self.do_auth_invalid(message)
        elif message.get('type', None) == "result":
            self.do_result(message)
        elif message.get('type', None) == "event":
            self.do_event(message)
        elif message.get('type', None) == "pong":
            self.do_pong(message)
        else:
            logging.warning("Unexpected message: ", message)

    def do_auth_required(self, m):
        logging.info("Home Assistant Web Socket Authorisation required")
        payload = {
                'type':'auth',
                'access_token': homeassistant_token
        }
        self._send(payload)

    def do_auth_invalid(self, message):
        logging.error("Home Assistant Web Socket Authorisation invalid: {}".format(message))

    def do_auth_complete(self):
        logging.info("Home Assistant Web Socket Authorisation complete")
        self.get_all_lights()
        self.subscribe_for_updates()

    def get_all_lights(self):
        discovery_result.clear()
        payload = {
            'type' : 'get_states'
        }
        self._send_with_id(payload, "getstates")

    def subscribe_for_updates(self):
        payload = {
            "type": "subscribe_events",
            "event_type": "state_changed"
        }
        self._send_with_id(payload, "subscribe")

    def change_light(self, address, light, data):
        service_data = {}
        service_data['entity_id'] = address['entity_id']

        payload = {
            "type": "call_service",
            "domain": "light",
            "service_data": service_data
        }

        payload["service"] = "turn_off"
        if 'state' in light and 'on' in light['state']:
            if light['state']['on']:
                payload["service"] = "turn_on"

        color_from_hsv = False
        for key, value in data.items():
            if key == "ct":
                service_data['color_temp'] = value
            if key == "bri":
                service_data['brightness'] = value
            if key == "xy":
                service_data['xy_color'] = [value[0], value[1]]
            if key == "hue":
                color_from_hsv = True
            if key == "sat":
                color_from_hsv = True
            if key == "on":
                if value:
                    payload["service"] = "turn_on"
                else:
                    payload["service"] = "turn_off"
            if key == "alert":
                service_data['alert'] = value
            if key == "transitiontime":
                service_data['transition'] = value / 10

        if color_from_hsv:
            service_data['hs_color'] = [data['hue'], data['sat']]

        self._send_with_id(payload, "service")


    def do_result(self, message):
        if 'result' in message and message['result']:
            message_type = self.id_to_type.pop(message['id'])
            if message_type == "getstates":
                latest_states.clear()
                for ha_state in message['result']:
                    if self._should_include(ha_state):
                        entity_id = ha_state.get('entity_id', None)
                        logging.info(f"Found {entity_id}")
                        latest_states[entity_id] = ha_state
                discovery_result.set()

    def do_event(self, message):
        try:
            event_type = message['event']['event_type']
            if event_type == 'state_changed':
                self.do_state_changed(message)
        except KeyError:
            logging.exception("No event_type  in event")

    def do_state_changed(self, message):
        try:
            entity_id = message['event']['data']['entity_id']
            new_state = message['event']['data']['new_state']
            if self._should_include(new_state):
                logging.debug("State update recevied for {}, new state {}".format(entity_id, new_state))
                latest_states[entity_id] = new_state
        except KeyError as e:
            logging.exception("No state in event: {}", message)

    def _should_include(self, ha_state):
        should_include = False
        diy_hue_flag = None
        entity_id = ha_state.get('entity_id', None)
        if entity_id.startswith("light."):
            if 'attributes' in ha_state and 'diyhue' in ha_state['attributes']:
                diy_hue_flag = ha_state['attributes']['diyhue']

            if include_by_default:
                if diy_hue_flag is not None and diy_hue_flag == "exclude":
                    should_include = False
                else:
                    should_include = True
            else:
                if diy_hue_flag is not None and diy_hue_flag == "include":
                    should_include = True
                else:
                    should_include = False
#        logging.debug("Home Asssitant Web Socket should include? {} - Include By Default? {}, Attribute: {} - State {}".format(should_include, include_by_default, diy_hue_flag, new_state))
        return should_include


    def _send_with_id(self, payload, type_of_call):
        payload['id'] = self.message_id
        self.id_to_type[self.message_id] = type_of_call
        self.message_id += 1
        self._send(payload)

    def _send(self, payload):
        json_payload = json.dumps(payload)
        self.send(json_payload)        

def connect_if_required():
    if homeassistant_ws_client is None or homeassistant_ws_client.client_terminated: 
        create_websocket_client()        

def create_websocket_client():
    global homeassistant_ws_client
    global next_connection_error_log
    global logging_backoff
    if time.time() >= next_connection_error_log:
        logging.warning("Home Assistant Web Socket Client disconnected trying to (re)connect")

    try:
        homeassistant_ws_client = HomeAssistantClient(homeassistant_url, protocols=['http-only', 'chat'])
        homeassistant_ws_client.connect()
        logging.info("Home Assistant Web Socket Client connected")
    except:
        if time.time() >= next_connection_error_log:
            logging.exception("Error connecting to Home Assistant WebSocket")
            next_connection_error_log = time.time() + logging_backoff
            logging_backoff = logging_backoff * 2
        homeassistant_ws_client = None


def create_ws_client(config, lights, adresses, sensors):
    global homeassistant_token
    global homeassistant_url
    global include_by_default
    if config['homeAssistantIp'] is not None:
        homeassistant_ip = config['homeAssistantIp']
    if config['homeAssistantPort'] is not None:
        homeAssistant_port = config['homeAssistantPort']
    if config['homeAssistantToken'] is not None:
        homeassistant_token = config['homeAssistantToken']
    if config['homeAssistantIncludeByDefault'] is not None:
        include_by_default = config['homeAssistantIncludeByDefault']

    homeassistant_url = f'ws://{homeassistant_ip}:{homeAssistant_port}/api/websocket'
    connect_if_required()


def discover(bridge_config, new_lights):
    logging.info("HomeAssistant WebSocket discovery called")
    connect_if_required()
    homeassistant_ws_client.get_all_lights()
    logging.info("HomeAssistant WebSocket discovery waiting for devices")
    completed = discovery_result.wait(timeout=discovery_timeout_seconds)
    logging.info("HomeAssistant WebSocket discovery devices received, timeout? {}".format((not completed)))
    # This only loops over discovered devices so we have already filtered out what we don't want
    for entity_id in latest_states.keys():
        ha_state = latest_states[entity_id]
        device_new = True
        light_name = ha_state["attributes"]["friendly_name"] if ha_state["attributes"]["friendly_name"] is not None else entity_id

        for lightkey in bridge_config["lights_address"].keys():
            if bridge_config["lights_address"][lightkey]["protocol"] == "homeassistant_ws":
                if bridge_config["lights_address"][lightkey]["entity_id"] == entity_id:
                    # Ensure any name change is saved
                    bridge_config["lights"][lightkey]['name'] = light_name
                    device_new = False
                    break
    
        if device_new:
            logging.info("HomeAssistant_ws: Adding light {}".format(light_name))
            new_light_id = nextFreeId(bridge_config, "lights")

            # 'entity_id', 'state', 'attributes', 'last_changed', 'last_updated', 'context'
            # From Home Assistant lights/__init.py__
            SUPPORT_BRIGHTNESS = 1
            SUPPORT_COLOR_TEMP = 2
            SUPPORT_EFFECT = 4
            SUPPORT_FLASH = 8
            SUPPORT_COLOR = 16
            SUPPORT_TRANSITION = 32
            SUPPORT_WHITE_VALUE = 128
            supported_features = ha_state['attributes']['supported_features']

            model_id = None
            if supported_features & SUPPORT_COLOR:
                model_id = "HomeAssistant-RGB"
            elif supported_features & SUPPORT_COLOR_TEMP:
                model_id = "HomeAssistant-WhiteAmbiance"
            elif supported_features & SUPPORT_BRIGHTNESS:
                model_id = "HomeAssistant-Dimmable"
            else:
                model_id = "HomeAssistant-Switch"

            diyhue_state = {}
            default_state = light_types[model_id]["state"]
            for key, value in default_state.items():
                diyhue_state[key] = value
            new_diyhue_state = translate_homeassistant_state_to_diyhue_state(default_state, ha_state)
            for k, v in new_diyhue_state.items():
                diyhue_state[k] = v

            bridge_config["lights"][new_light_id] = {
                "type": light_types[model_id]["type"],
                "name": light_name,
                "uniqueid": "4a:e0:ad:7f:cf:" + str(
                    random.randrange(0, 99)) + "-1",
                "modelid": light_types[model_id]["modelid"], 
                "manufacturername": light_types[model_id]["manufacturername"],
                "swversion": light_types[model_id]["swversion"],
                "capabilities": light_types[model_id]["capabilities"],
                "config": light_types[model_id]["config"],
                "state": diyhue_state,
            }
            new_lights.update({new_light_id: {"name": light_name}})
            bridge_config["lights_address"][new_light_id] = {
                "protocol": "homeassistant_ws",
                "entity_id": entity_id,
                # Required or we get an error in HueEmulator3.splitLightsToDevices
                "ip":"none"
            }

            # Now add to room if required
            ha_room_name = None
            ha_zone_name = None
            ha_group_name = None

            if "diyhue_room" in ha_state['attributes']:
                ha_room_name = ha_state['attributes']["diyhue_room"]

            elif "diyhue_zone" in ha_state['attributes']:
                ha_room_name = ha_state['attributes']["diyhue_zone"]
            elif "diyhue_group" in ha_state['attributes']:
                ha_room_name = ha_state['attributes']["diyhue_group"]

            ha_class = "Other" # Default to Other but can pull from HA
            if "diyhue_class" in ha_state['attributes']:
                ha_class = ha_state['attributes']["diyhue_class"]

            room_new = False if ha_room_name is None else True
            zone_new = False if ha_zone_name is None else True
            group_new = False if ha_group_name is None else True

            for groupkey in bridge_config["groups"].keys():
                logging.info(f"Checking {groupkey} for {ha_room_name}")
                if room_new and bridge_config["groups"][groupkey]["name"] == ha_room_name and bridge_config["groups"][groupkey]["type"] == "Room":
                    room_new = False
                    if new_light_id not in bridge_config["groups"][groupkey]["lights"]:
                        bridge_config["groups"][groupkey]["lights"].append(new_light_id)
                        logging.info(f"Home Assistant adding {entity_id} to existing room {ha_room_name}")
                if zone_new and bridge_config["groups"][groupkey]["name"] == ha_zone_name and bridge_config["groups"][groupkey]["type"] == "Zone":
                    zone_new = False
                    if new_light_id not in bridge_config["groups"][groupkey]["lights"]:
                        bridge_config["groups"][groupkey]["lights"].append(new_light_id)
                        logging.info(f"Home Assistant adding {entity_id} to existing zone {ha_zone_name}")

                if group_new and bridge_config["groups"][groupkey]["name"] == ha_group_name and bridge_config["groups"][groupkey]["type"] == "LightGroup":
                    group_new = False
                    if new_light_id not in bridge_config["groups"][groupkey]["lights"]:
                        bridge_config["groups"][groupkey]["lights"].append(new_light_id)
                        logging.info(f"Home Assistant adding {entity_id} to existing group {ha_group_name}")
                if not room_new and not zone_new and not group_new:
                    # We aren't looking for anymore so break
                    break

            if room_new:
                new_room_id = nextFreeId(bridge_config, "groups")
                bridge_config["groups"][new_room_id] = {
                    "action": {"on": False}, 
                    "state": {"any_on": False, 
                    "all_on": False},
                    "lights": [ new_light_id ],
                    "name": ha_room_name,
                    "class" : ha_class,
                    "type": "Room",
                }
                logging.info(f"Home Assistant adding {entity_id} to new room {ha_room_name}")

            if zone_new:
                new_zone_id = nextFreeId(bridge_config, "groups")
                bridge_config["groups"][new_zone_id] = {
                    "action": {"on": False}, 
                    "state": {"any_on": False, "all_on": False},
                    "lights": [ new_light_id ],
                    "name": ha_zone_name,
                    "class" : ha_class,
                    "type": "Zone",
                }
                logging.info(f"Home Assistant adding {entity_id} to new zone {ha_zone_name}")

            if group_new:
                new_group_id = nextFreeId(bridge_config, "groups")
                bridge_config["groups"][new_group_id] = {
                    "action": {"on": False}, 
                    "state": {"any_on": False, "all_on": False},
                    "lights": [ new_light_id ],
                    "name": ha_group_name,
                    "type": "LightGroup",
                }
                logging.info(f"Home Assistant adding {entity_id} to new group {ha_group_name}")
    logging.info("HomeAssistant WebSocket discovery complete")

def translate_homeassistant_state_to_diyhue_state(existing_diy_hue_state, ha_state):
    '''
    Home Assistant:
    {
        "entity_id": "light.my_light", 
        "state": "off", 
        "attributes": {
            "min_mireds": 153, 
            "max_mireds": 500, 
            # If using color temp
            "brightness": 254, "color_temp": 345, 
            # If using colour:
            "brightness": 254, "hs_color": [262.317, 64.314], "rgb_color": [151, 90, 255], "xy_color": [0.243, 0.129]
            "effect_list": ["colorloop", "random"], 
            "friendly_name": "My Light", 
            "supported_features": 63
        }, 
        "last_changed": "2020-12-09T17:46:40.569891+00:00", 
        "last_updated": "2020-12-09T17:46:40.569891+00:00", 
    }    

    Diy Hue:
    "state": {
.        "alert": "select",
        "bri": 249,
        # Either ct, hs or xy 
        # If ct then uses ct
        # If xy uses xy
        # If hs uses hue/sat
        "colormode": "xy",
.        "effect": "none",
        "ct": 454,
        "hue": 0,
        "on": true,
.        "reachable": true,
        "sat": 0,
        "xy": [
            0.478056,
            0.435106
        ]
    },
    '''
    # Copy existing state into new dict
    diyhue_state = {}
    for key,value in existing_diy_hue_state.items():
        diyhue_state[key] = value
        
    # Overwrite any values set by the latest HA State
    reachable = False
    is_on = False
    if "state" in ha_state and ha_state['state'] in ['on','off']:
        reachable = True
        is_on = ha_state['state'] == 'on'

    diyhue_state["reachable"] = reachable
    diyhue_state["on"] = is_on
    if "attributes" in ha_state:
        for key, value in ha_state['attributes'].items():
            if key == "brightness":
                diyhue_state['bri'] = value
            if key == "color_temp":
                diyhue_state['ct'] = value
                diyhue_state['colormode'] = 'ct'
            if key == "xy_color":
                diyhue_state['xy'] = [value[0], value[1]]
                diyhue_state['colormode'] = 'xy'

#    logging.info("Translate, in state {}, out state: {}".format(ha_state, diyhue_state))
    return diyhue_state

def set_light(address, light, data):
    connect_if_required()            
    homeassistant_ws_client.change_light(address, light, data)

def get_light_state(address, light):
    connect_if_required()
    entity_id = address.get('entity_id', None)
    if entity_id is None:
        return { 'reachable': False }
    homeassistant_state = latest_states[entity_id]
    existing_diy_hue_state = light.get('state', {})
    return translate_homeassistant_state_to_diyhue_state(existing_diy_hue_state, homeassistant_state)
