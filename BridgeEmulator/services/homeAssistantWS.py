import logManager
import json
import time
import threading
from ws4py.client.threadedclient import WebSocketClient

logging = logManager.logger.get_logger(__name__)


discovery_timeout_seconds = 60
discovery_result = threading.Event()
next_connection_error_log = 0
logging_backoff = 2  # 2 Second back off
homeassistant_token = ''
homeassistant_url = 'ws://127.0.0.1:8123/api/websocket'
homeassistant_ws_client = None
include_by_default = False
use_https = False

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
        logging.info(
            "Home Assistant WebSocket Connection Closed. Code: {} Reason {}".format(code, reason))
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
            'type': 'auth',
            'access_token': homeassistant_token
        }
        self._send(payload)

    def do_auth_invalid(self, message):
        logging.error(
            "Home Assistant Web Socket Authorisation invalid: {}".format(message))

    def do_auth_complete(self):
        logging.info("Home Assistant Web Socket Authorisation complete")
        self.get_all_lights()
        self.subscribe_for_updates()

    def get_all_lights(self):
        discovery_result.clear()
        payload = {
            'type': 'get_states'
        }
        self._send_with_id(payload, "getstates")

    def subscribe_for_updates(self):
        payload = {
            "type": "subscribe_events",
            "event_type": "state_changed"
        }
        self._send_with_id(payload, "subscribe")

    def change_light(self, light, data):
        service_data = {}
        service_data['entity_id'] = light.protocol_cfg['entity_id']
        if light.protocol_cfg['entity_id'].startswith("light."):
            payload = {
                "type": "call_service",
                "domain": "light",
                "service_data": service_data
            }
        elif light.protocol_cfg['entity_id'].startswith("switch."):
            payload = {
                "type": "call_service",
                "domain": "switch",
                "service_data": service_data
            }
        payload["service"] = "turn_on"
        if 'on' in data:
            if not data['on']:
                payload["service"] = "turn_off"

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
                service_data['flash'] = "long"
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
                logging.debug("State update recevied for {}, new state {}".format(
                    entity_id, new_state))
                latest_states[entity_id] = new_state
        except KeyError as e:
            logging.exception("No state in event: {}", message)

    def _should_include(self, ha_state):
        should_include = False
        diy_hue_flag = None
        entity_id = ha_state.get('entity_id', None)
        if entity_id.startswith("light.") or entity_id.startswith("switch."):
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

    return homeassistant_ws_client


def create_websocket_client():
    global homeassistant_ws_client
    global next_connection_error_log
    global logging_backoff
    if time.time() >= next_connection_error_log:
        logging.warning(
            "Home Assistant Web Socket Client disconnected trying to (re)connect")

    try:
        homeassistant_ws_client = HomeAssistantClient(
            homeassistant_url, protocols=['http-only', 'chat'])
        homeassistant_ws_client.connect()
        logging.info("Home Assistant Web Socket Client connected")
    except:
        if time.time() >= next_connection_error_log:
            logging.exception("Error connecting to Home Assistant WebSocket")
            next_connection_error_log = time.time() + logging_backoff
            logging_backoff = logging_backoff * 2
        homeassistant_ws_client = None


def create_ws_client(bridgeConfig):
    global homeassistant_token
    global homeassistant_url
    global include_by_default
    if 'homeAssistantIp' in bridgeConfig["config"]["homeassistant"]:
        homeassistant_ip = bridgeConfig["config"]["homeassistant"]['homeAssistantIp']
    if 'homeAssistantPort' in bridgeConfig["config"]["homeassistant"]:
        homeAssistant_port = bridgeConfig["config"]["homeassistant"]['homeAssistantPort']
    if 'homeAssistantToken' in bridgeConfig["config"]["homeassistant"]:
        homeassistant_token = bridgeConfig["config"]["homeassistant"]['homeAssistantToken']
    if 'homeAssistantIncludeByDefault' in bridgeConfig["config"]["homeassistant"]:
        include_by_default = bridgeConfig["config"]["homeassistant"]['homeAssistantIncludeByDefault']
    if 'homeAssistantUseHttps' in bridgeConfig["config"]["homeassistant"]:
        use_https = bridgeConfig["config"]["homeassistant"]['homeAssistantUseHttps']

    ws_prefix = "ws"
    if use_https:
        ws_prefix = "wss"

    homeassistant_url = f'{ws_prefix}://{homeassistant_ip}:{homeAssistant_port}/api/websocket'
    connect_if_required()


def discover(detectedLights):
    logging.info("HomeAssistant WebSocket discovery called")
    connect_if_required()
    homeassistant_ws_client.get_all_lights()
    logging.info("HomeAssistant WebSocket discovery waiting for devices")
    completed = discovery_result.wait(timeout=discovery_timeout_seconds)
    logging.info("HomeAssistant WebSocket discovery devices received, timeout? {}".format(
        (not completed)))
    # This only loops over discovered devices so we have already filtered out what we don't want
    for entity_id in latest_states.keys():
        ha_state = latest_states[entity_id]
        device_new = True
        lightName = ha_state["attributes"]["friendly_name"] if "friendly_name" in ha_state["attributes"] else entity_id

        logging.info("HomeAssistant_ws: found light {}".format(lightName))
        # From Home Assistant lights/__init.py__
        UNKNOWN = "unknown"  # Ambiguous color mode
        ONOFF = "onoff"  # Must be the only supported mode
        BRIGHTNESS = "brightness"  # Must be the only supported mode
        COLOR_TEMP = "color_temp"
        HS = "hs"
        XY = "xy"
        RGB = "rgb"
        RGBW = "rgbw"
        RGBWW = "rgbww"
        WHITE = "white"  # Must *NOT* be the only supported mode

        supported_colourmodes = ha_state.get('attributes', {}).get('supported_color_modes', [])

        model_id = None
        if HS in supported_colourmodes or XY in supported_colourmodes or RGB in supported_colourmodes or RGBW in supported_colourmodes or RGBWW in supported_colourmodes:
            model_id = "LCT015"
        elif COLOR_TEMP in supported_colourmodes:
            model_id = "LTW001"
        elif BRIGHTNESS in supported_colourmodes:
            model_id = "LWB010"
        else:
            model_id = "LOM001"

        protocol_cfg = {"entity_id": entity_id,
                        "ip": "none"}

        detectedLights.append({"protocol": "homeassistant_ws", "name": lightName, "modelid": model_id, "protocol_cfg": protocol_cfg})

    logging.info("HomeAssistant WebSocket discovery complete")
