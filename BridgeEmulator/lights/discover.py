import logManager
import configManager
import socket
import json
import uuid
from time import sleep
from datetime import datetime, timezone
from lights.protocols import tpkasa, wled, mqtt, hyperion, yeelight, hue, deconz, native_multi, tasmota, shelly, esphome, tradfri, elgato
from services import homeAssistantWS
from HueObjects import Light, StreamEvent
from functions.core import nextFreeId
from lights.light_types import lightTypes
logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Very short timeout. If scanning fails this could be increased
    sock.settimeout(0.02)
    result = sock.connect_ex((host, port))
    sock.close()
    return result


def iter_ips(port):
    argsDict = configManager.runtimeConfig.arg
    HOST_IP = argsDict["HOST_IP"]
    scan_on_host_ip = argsDict["scanOnHostIP"]
    ip_range_start = argsDict["IP_RANGE_START"]
    ip_range_end = argsDict["IP_RANGE_END"]
    host = HOST_IP.split('.')
    if scan_on_host_ip:
        yield ('127.0.0.1', port)
        return
    for addr in range(ip_range_start, ip_range_end + 1):
        host[3] = str(addr)
        test_host = '.'.join(host)
        if test_host != HOST_IP:
            yield (test_host, port)


def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts


def addNewLight(modelid, name, protocol, protocol_cfg):
    newLightID = nextFreeId(bridgeConfig, "lights")
    if modelid in lightTypes:
        light = lightTypes[modelid]
        light["name"] = name
        light["id_v1"] = newLightID
        light["modelid"] = modelid
        light["protocol"] = protocol
        light["protocol_cfg"] = protocol_cfg
        newObject = Light.Light(light)
        bridgeConfig["lights"][newLightID] = newObject
        bridgeConfig["groups"]["0"].add_light(newObject)
        # trigger stream messages
        rooms = []
        lights = []
        for group, obj in bridgeConfig["groups"].items():
            rooms.append(obj.id_v2)
        for light, obj in bridgeConfig["lights"].items():
            lights.append(obj.id_v2)
        bridgeConfig["groups"]["0"].groupZeroStream(rooms, lights)
        configManager.bridgeConfig.save_config(backup=False, resource="lights")

        return newLightID
    return False


def manualAddLight(ip, protocol, config={}):
    modelid = config["lightModelID"] if "lightModelID" in config else "LCT015"
    name = config["lightName"] if "lightName" in config else "New Light"
    if protocol == "auto":
        detectedLights = []
        native_multi.discover(detectedLights, [ip])
        tasmota.discover(detectedLights, [ip])
        shelly.discover(detectedLights, [ip])
        esphome.discover(detectedLights, [ip])
        if len(detectedLights) >= 1:
            for x in range(len(detectedLights)):
                logging.info(
                    "Found light " + detectedLights[x]["protocol"] + " " + detectedLights[x]["name"])
                addNewLight(detectedLights[x]["modelid"], detectedLights[x]["name"],
                            detectedLights[x]["protocol"], detectedLights[x]["protocol_cfg"])

    else:
        config["ip"] = ip
        addNewLight(modelid, name, protocol, config)

def discoveryEvent():
    streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "data": [{
                        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'zigbee_device_discovery')),
                        "owner": {
                            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'device')),
                            "rtype": "device"
                        },
                        "status": bridgeConfig["config"]["zigbee_device_discovery_info"]["status"],
                        "type": "zigbee_device_discovery"
                        }],
                    "id": str(uuid.uuid4()),
                    "type": "update"
                    }
    StreamEvent(streamMessage)



def scanForLights():  # scan for ESP8266 lights and strips
    logging.info("scan for light")
    bridgeConfig["temp"]["scanResult"] = {"lastscan": "active"}
    discoveryEvent()
    detectedLights = []

    if bridgeConfig["config"]["port"]["enabled"]:
        device_ips = []
        for ports in bridgeConfig["config"]["port"]["ports"]:
            # return all host that listen on ports in list config
            device_ips += find_hosts(ports)
    else:
        # return all host that listen on port 80
        device_ips = find_hosts(80)


    # return all host that listen on port 80
    #device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    if bridgeConfig["config"]["mqtt"]["enabled"]:
        # brioadcast MQTT message, lights will be added by the service
        mqtt.discover(bridgeConfig["config"]["mqtt"])
    if bridgeConfig["config"]["deconz"]["enabled"]:
        deconz.discover(detectedLights, bridgeConfig["config"]["deconz"])
    if bridgeConfig["config"]["homeassistant"]["enabled"]:
        homeAssistantWS.discover(detectedLights)
    if bridgeConfig["config"]["yeelight"]["enabled"]:
        yeelight.discover(detectedLights)
    # native_multi probe all esp8266 lights with firmware from diyhue repo
    if bridgeConfig["config"]["native_multi"]["enabled"]:
        native_multi.discover(detectedLights, device_ips)
    if bridgeConfig["config"]["tasmota"]["enabled"]:
        tasmota.discover(detectedLights, device_ips)
    if bridgeConfig["config"]["wled"]["enabled"]:
        # Most of the other discoveries are disabled by having no IP address (--disable-network-scan)
        # But wled does an mdns discovery as well.
        wled.discover(detectedLights, device_ips)
    hue.discover(detectedLights, bridgeConfig["config"]["hue"])
    if bridgeConfig["config"]["shelly"]["enabled"]:
        shelly.discover(detectedLights, device_ips)
    if bridgeConfig["config"]["esphome"]["enabled"]:
        esphome.discover(detectedLights, device_ips)
    tradfri.discover(detectedLights, bridgeConfig["config"]["tradfri"])
    if bridgeConfig["config"]["hyperion"]["enabled"]:
        hyperion.discover(detectedLights)
    if bridgeConfig["config"]["tpkasa"]["enabled"]:
        tpkasa.discover(detectedLights)
    if bridgeConfig["config"]["elgato"]["enabled"]:
        # Scan with port 9123 before mDNS discovery
        elgato_ips = find_hosts(9123)
        logging.info(pretty_json(elgato_ips))
        elgato.discover(detectedLights, elgato_ips)
    bridgeConfig["temp"]["scanResult"]["lastscan"] = datetime.now().strftime(
        "%Y-%m-%dT%H:%M:%S")
    for light in detectedLights:
        # check if light is already present
        lightIsNew = True
        for key, lightObj in bridgeConfig["lights"].items():
            if lightObj.protocol == light["protocol"]:
                if light["protocol"] == "native_multi":
                    # check based on mac address and modelid
                    if lightObj.protocol_cfg["mac"] == light["protocol_cfg"]["mac"] and lightObj.protocol_cfg["light_nr"] == light["protocol_cfg"]["light_nr"] and lightObj.modelid == light["modelid"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                        break
                elif light["protocol"] in ["yeelight", "tasmota", "tradfri", "hyperion", "tpkasa"]:
                    # check based on id and modelid
                    if lightObj.protocol_cfg["id"] == light["protocol_cfg"]["id"] and lightObj.modelid == light["modelid"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                elif light["protocol"] in ["shelly", "native", "native_single", "esphome"]:
                    # check based on mac address and modelid
                    if lightObj.protocol_cfg["mac"] == light["protocol_cfg"]["mac"] and lightObj.modelid == light["modelid"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                elif light["protocol"] in ["hue", "deconz"]:
                    # check based on light uniqueid and modelid
                    if lightObj.protocol_cfg["uniqueid"] == light["protocol_cfg"]["uniqueid"]  and lightObj.modelid == light["modelid"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                elif light["protocol"] in ["wled"]:
                    # Check based on mac and segment and modelid
                    if lightObj.protocol_cfg["mac"] == light["protocol_cfg"]["mac"] and lightObj.protocol_cfg["segmentId"] == light["protocol_cfg"]["segmentId"] and lightObj.modelid == light["modelid"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                elif light["protocol"] == "homeassistant_ws":
                    # Check based on entity_id and modelid
                    if lightObj.protocol_cfg["entity_id"] == light["protocol_cfg"]["entity_id"] and lightObj.modelid == light["modelid"]:
                        lightIsNew = False
                elif light["protocol"] == "elgato":
                    # check based on mac address and modelid
                    if lightObj.protocol_cfg['mac'] == light["protocol_cfg"]['mac'] and lightObj.modelid == light["modelid"]:
                        lightIsNew = False
        if lightIsNew:
            logging.info("Add new light " + light["name"])
            lightId = addNewLight(
                light["modelid"], light["name"], light["protocol"], light["protocol_cfg"])
            bridgeConfig["temp"]["scanResult"][lightId] = {
                "name": light["name"]}
    bridgeConfig["config"]["zigbee_device_discovery_info"]["status"] = "ready"
    discoveryEvent()
    return bridgeConfig["temp"]["scanResult"]
