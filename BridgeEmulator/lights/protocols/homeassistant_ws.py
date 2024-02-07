import logManager
from services.homeAssistantWS import connect_if_required, latest_states
from pprint import pprint
logging = logManager.logger.get_logger(__name__)

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
    if "attributes" in ha_state and is_on:  # Home assistant only reports attributes if light is on
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

def set_light(light, data):
    connection = connect_if_required()
    connection.change_light(light, data)

def get_light_state(light):
    connect_if_required()
    entity_id = light.protocol_cfg["entity_id"]
    homeassistant_state = latest_states[entity_id]
    existing_diy_hue_state = light.state
    # pprint(translate_homeassistant_state_to_diyhue_state(existing_diy_hue_state, homeassistant_state))
    return translate_homeassistant_state_to_diyhue_state(existing_diy_hue_state, homeassistant_state)
