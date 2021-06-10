import logManager
import configManager
import socket
import json
from time import sleep
from datetime import datetime
from services.deconz import scanDeconz
from lights.protocols import wled, mqtt, hyperion, yeelight, hue, deconz, native, native_single, native_multi, tasmota, shelly, esphome, tradfri
import HueObjects
from functions.core import nextFreeId
from lights.light_types import lightTypes
logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
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
        bridgeConfig["lights"][newLightID] = HueObjects.Light(light)
        bridgeConfig["groups"]["0"].add_light(bridgeConfig["lights"][newLightID])
        configManager.bridgeConfig.save_config(backup=False, resource="lights")
        return newLightID
    return False

def manualAddLight(ip, protocol, modelid="LCT015", name="", config={}):
    if protocol == "auto":
        detectedLights = []
        native_multi.discover(detectedLights,[ip])
        tasmota.discover(detectedLights,[ip])
        shelly.discover(detectedLights,[ip])
        esphome.discover(detectedLights,[ip])
        if len(detectedLight) == 1:
            logging.info("Found light " + detectedLights[0]["protocol"] + " " + detectedLights[0]["name"])
            addNewLight(detectedLight[0]["modelid"], detectedLight[0]["name"], detectedLight[0]["protocol"], detectedLight[0]["protocol_cfg"])
    else:
        addNewLight(modelid, name, protocol, config)

def scanForLights(): #scan for ESP8266 lights and strips
    bridgeConfig["temp"]["scanResult"] = {"lastscan": "active"}
    detectedLights = []
    #return all host that listen on port 80
    device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    if bridgeConfig["config"]["mqtt"]["enabled"]:
        mqtt.discover(bridgeConfig["config"]["mqtt"]) # brioadcast MQTT message, lights will be added by the service
    if bridgeConfig["config"]["deconz"]["enabled"]:
        deconz.discover(detectedLights, bridgeConfig["config"]["deconz"])
    yeelight.discover(detectedLights)
    native_multi.discover(detectedLights,device_ips) # native_multi probe all esp8266 lights with firmware from diyhue repo
    tasmota.discover(detectedLights,device_ips)
    wled.discover(detectedLights,device_ips)
    hue.discover(detectedLights, bridgeConfig["config"]["hue"])
    shelly.discover(detectedLights,device_ips)
    esphome.discover(detectedLights,device_ips)
    tradfri.discover(detectedLights, bridgeConfig["config"]["tradfri"])
    hyperion.discover(detectedLights)
    bridgeConfig["temp"]["scanResult"]["lastscan"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for light in detectedLights:
        # check if light is already present
        lightIsNew = True
        for key, lightObj in bridgeConfig["lights"].items():
            if lightObj.protocol == light["protocol"]:
                if light["protocol"] == "native_multi":
                     if lightObj.protocol_cfg["mac"] == light["protocol_cfg"]["mac"] and lightObj.protocol_cfg["light_nr"] == light["protocol_cfg"]["light_nr"]:
                         logging.info("Update IP for light " + light["name"])
                         lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                         lightIsNew = False
                         break
                elif light["protocol"] in ["yeelight", "tasmota", "tradfri", "hyperion"]:
                    if lightObj.protocol_cfg["id"] == light["protocol_cfg"]["id"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                elif light["protocol"] in ["shelly", "native", "native_single", "esphome"]:
                    # check based on mac address
                    if lightObj.protocol_cfg["mac"] == light["protocol_cfg"]["mac"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                elif  light["protocol"] in  ["hue", "deconz"]:
                    # check based on light uniqueid
                    if lightObj.protocol_cfg["uniqueid"] == light["protocol_cfg"]["uniqueid"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
                elif light["protocol"] in ["wled"]:
                    # Check mac and segment
                    if lightObj.protocol_cfg["mac"] == light["protocol_cfg"]["mac"] and lightObj.protocol_cfg["segmentId"] == light["protocol_cfg"]["segmentId"]:
                        logging.info("Update IP for light " + light["name"])
                        lightObj.protocol_cfg["ip"] = light["protocol_cfg"]["ip"]
                        lightIsNew = False
        if lightIsNew:
            logging.info("Add new light " + light["name"])
            lightId = addNewLight(light["modelid"], light["name"], light["protocol"], light["protocol_cfg"])
            bridgeConfig["temp"]["scanResult"][lightId] = {"name": light["name"]}
    return bridgeConfig["temp"]["scanResult"]
