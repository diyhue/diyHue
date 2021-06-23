import json
import logManager
import requests

logging = logManager.logger.get_logger(__name__)

#bridgeConfig = configManager.bridgeConfig.yaml_config
#newLights = configManager.runtimeConfig.newLights

def sendRequest(url, timeout=3):
    head = {"Content-type": "application/json"}
    response = requests.get(url, timeout=timeout, headers=head)
    return response.text


def discover(detectedLights, device_ips):
    logging.debug("shelly: <discover> invoked!")
    for ip in device_ips:
        try:
            logging.debug("shelly: probing ip " + ip)
            response = requests.get("http://" + ip + "/shelly", timeout=3)
            if response.status_code == 200:
                device_data = json.loads(response.text)
                if device_data["type"] == "SHSW-1":

                    logging.debug("shelly: " + ip + " is a shelly device ")
                    shelly_response = requests.get("http://" + ip + "/status", timeout=5)
                    shelly_data = json.loads(shelly_response.text)
                    logging.debug("shelly: ip: " + shelly_data["wifi_sta"]["ip"])
                    logging.debug("shelly: Mac:      " + shelly_data["mac"])
                    detectedLights.append({"protocol": "shelly", "name": ip, "modelid": "LOM001", "protocol_cfg": {"ip": ip, "mac": shelly_data["mac"]}})

        except Exception as e:
            logging.debug("shelly: ip " + ip + " is unknow device, " + str(e))


def set_light(light, data):
    logging.debug("shelly: <set_light> invoked! IP=" + light.protocol_cfg["ip"])

    for key, value in data.items():
        if key == "on":
            if value:
                sendRequest("http://" + light.protocol_cfg["ip"] + "/relay/0/?turn=on")
            else:
                sendRequest("http://" + light.protocol_cfg["ip"] + "/relay/0/?turn=off")


def get_light_state(light):
    logging.debug("shelly: <get_light_state> invoked!")
    data = sendRequest("http://" + light.protocol_cfg["ip"] + "/relay/0")
    light_data = json.loads(data)
    state = {}

    if 'ison' in light_data:
        state['on'] = True if light_data["ison"] == "true" else False
    return state
