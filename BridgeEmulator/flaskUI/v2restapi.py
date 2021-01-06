import configManager
import logManager
import uuid
import json
from subprocess import Popen
from lights.manage import sendLightRequest
from flask_restful import Resource
from flask import request

logging = logManager.logger.get_logger(__name__)


bridgeConfig = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
newLights = configManager.runtimeConfig.newLights

def authorizeV2(headers):
    if "hue-application-key" in headers and headers["hue-application-key"] in bridgeConfig["config"]["whitelist"]:
        return {"user": headers["hue-application-key"]}
    return []


def buildV2Scene(sceneId):
    v1Scene = bridgeConfig["emulator"]["links"]["v2"]["scene"][sceneId]
    v2Scene = {"actions":[]}
    for light, state in bridgeConfig["scenes"][v1Scene]["lightstates"].items():
        v2State = {}
        if "on" in state:
            v2State["on"] = {"on": state["on"]}
        if "bri" in state:
            v2State["dimming"] = {"brightness": state["bri"]}
        if "xy" in state:
            v2State["color"] = {"xy": {"x": state["xy"][0], "y": state["xy"][1]}}
        if "ct" in state:
            v2State["color_temperature"] = {"mirek": state["ct"]}

        v2Scene["actions"].append(
            {
                "action": v2State,
                "target": {
                    "reference_id": bridgeConfig["emulator"]["links"]["v1"]["lights"][light],
                    "reference_type": "light",
                    "rid": bridgeConfig["emulator"]["links"]["v1"]["lights"][light],
                    "rtype": "light",
                },
            }
        )

    if "group" in bridgeConfig["scenes"][v1Scene]:
        v2Scene["group"] = {
            "reference_id": bridgeConfig["emulator"]["links"]["v1"]["groups"][bridgeConfig["scenes"][v1Scene]["group"]],
            "reference_type": "room",
            "rid": bridgeConfig["emulator"]["links"]["v1"]["groups"][bridgeConfig["scenes"][v1Scene]["group"]],
            "rtype": "room"
        }
    v2Scene["metadata"] = {}
    v2Scene["id"] = sceneId
    v2Scene["id_v1"] = "/scenes/" + v1Scene
    v2Scene["name"] = bridgeConfig["scenes"][v1Scene]["name"]
    v2Scene["type"] = "scene"
    return v2Scene

def buildV2Light(uuid):
    v1Light = bridgeConfig["emulator"]["links"]["v2"]["light"][uuid]["id_v1"]
    v2Light = {}
    if "xy" in bridgeConfig["lights"][v1Light]["state"]:
        v2Light = {
            "color": {
                "gamut": {
                    "blue": {"x": 0.1532, "y": 0.0475},
                    "green": {"x": 0.17, "y": 0.7},
                    "red": {"x": 0.6915, "y": 0.3083},
                },
                "gamut_type": "C",
                "xy": {
                    "x": bridgeConfig["lights"][v1Light]["state"]["xy"][0],
                    "y": bridgeConfig["lights"][v1Light]["state"]["xy"][1]
                }
            }
        }
    if "ct" in bridgeConfig["lights"][v1Light]["state"]:
        v2Light["color_temperature"] = {
            "mirek": bridgeConfig["lights"][v1Light]["state"]["ct"]
        }
    if "bri" in bridgeConfig["lights"][v1Light]["state"]:
        v2Light["dimming"] = {
            "brightness": bridgeConfig["lights"][v1Light]["state"]["bri"]
        }
    v2Light["dynamics"] = {}
    v2Light["id"] = uuid
    v2Light["id_v1"] = "/lights/" + v1Light
    v2Light["metadata"] = {"name": bridgeConfig["lights"][v1Light]["name"]}
    if "archetype" in bridgeConfig["lights"][v1Light]["config"]:
        v2Light["metadata"]["archetype"] = bridgeConfig["lights"][v1Light]["config"]["archetype"]
    v2Light["mode"] = "normal"
    v2Light["on"] = {
        "on": bridgeConfig["lights"][v1Light]["state"]["on"]
    }
    v2Light["type"] = "light"
    return v2Light


def buildV2Room(uuid):
    v1Group = bridgeConfig["emulator"]["links"]["v2"]["room"][uuid]["id_v1"]
    v2Room = {"grouped_services": [], "services": []}
    v2Room["grouped_services"].append({
        "reference_id": bridgeConfig["emulator"]["links"]["v2"]["room"][uuid]["groupedLightsUuid"],
        "reference_type": "grouped_light",
        "rid": bridgeConfig["emulator"]["links"]["v2"]["room"][uuid]["groupedLightsUuid"],
        "rtype": "grouped_light"

    })
    v2Room["id"] = uuid
    v2Room["id_v1"] =  "/groups/" + v1Group
    v2Room["metadata"] = {
        "archetype": bridgeConfig["groups"][v1Group]["class"].replace(" ", "_").replace("'", "").lower(),
        "name": bridgeConfig["groups"][v1Group]["name"]
        }
    for light in bridgeConfig["groups"][v1Group]["lights"]:
        v2Room["services"].append({
          "reference_id": bridgeConfig["emulator"]["links"]["v1"]["lights"][light],
          "reference_type": "light",
          "rid": bridgeConfig["emulator"]["links"]["v1"]["lights"][light],
          "rtype": "light"
        })

    v2Room["type"] = "room"
    return v2Room

def buildV2GroupedLight(uuid):
    v1Group = bridgeConfig["emulator"]["links"]["v2"]["groupedLights"][uuid]["id_v1"]
    v2Group = {}
    v2Group["id"] = uuid
    v2Group["id_v1"] =  "/groups/" + v1Group
    v2Group["on"] = {"on": bridgeConfig["groups"][v1Group]["state"]["any_on"] if v1Group != "0" else True}
    v2Group["type"] = "grouped_light"
    return v2Group


def buildV2ZigBeeConnect(uuid):
    id_v1 = bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"][uuid]["id_v1"]
    result = {}
    result["id"] = uuid
    result["id_v1"] =  "/" + bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"][uuid]["resource"] + "/" + id_v1 if id_v1 != "" else ""
    result["mac_address"] = bridgeConfig[bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"][uuid]["resource"]][id_v1]["uniqueid"][:23] if id_v1 != "" else "00:17:88:01:01:59:84:2e"
    result["status"] = "connected"
    result["type"] = "zigbee_connectivity"
    return result

def buildV2Entertainment(uuid):
    id_v1 = bridgeConfig["emulator"]["links"]["v2"]["entertainment"][uuid]["id_v1"]
    result = {
        "id": uuid,
        "id_v1": "/lights/" + id_v1 if id_v1 != "" else "",
        "proxy": bridgeConfig["lights"][id_v1]["capabilities"]["streaming"]["proxy"] if id_v1 != "" else True,
        "renderer": bridgeConfig["lights"][id_v1]["capabilities"]["streaming"]["renderer"] if id_v1 != "" else False
        }
    if id_v1 != "":
        result["segments"] = {
            "configurable": False,
            "max_segments": 1,
            "segments": [
                {
                    "length": 1,
                     "start": 0
                }
            ]
        }
    result["type"] = "entertainment"
    return result

def buildV2EntertainmentConfig(uuid):
    id_v1 = bridgeConfig["emulator"]["links"]["v2"]["entertainment_configuration"][uuid]["id_v1"]
    result = {
      "channels": [],
      "configuration_type": "screen",
      "id": uuid,
      "id_v1": "/groups/" + id_v1,
      "locations": {
        "service_locations": []
      },
      "name": bridgeConfig["groups"][id_v1]["name"],
      "status": "active" if bridgeConfig["groups"][id_v1]["stream"]["active"] else "inactive",
      "stream_proxy": {
        "mode": "auto",
        "node": {
          "reference_id": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["uuid"],
          "reference_type": "entertainment",
          "rid": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["uuid"],
          "rtype": "entertainment"
        }
      },
      "type": "entertainment_configuration"

    }
    index = 0
    for light in bridgeConfig["groups"][id_v1]["lights"]:
        lightUuid = bridgeConfig["emulator"]["links"]["v1"]["lights"][light]
        entertainmentUuid = bridgeConfig["emulator"]["links"]["v2"]["light"][lightUuid]["entertianmentUuid"]
        result["channels"].append({
          "channel_id": index,
          "members": [
            {
              "index": 0,
              "service": {
                "reference_id": entertainmentUuid,
                "reference_type": "entertainment",
                "rid": entertainmentUuid,
                "rtype": "entertainment"
              }
            }
          ],
          "position": {
            "x": bridgeConfig["groups"][id_v1]["locations"][light][0],
            "y": bridgeConfig["groups"][id_v1]["locations"][light][1],
            "z": bridgeConfig["groups"][id_v1]["locations"][light][2]
          }
        })
        result["locations"]["service_locations"].append({
          "position": {
            "x": bridgeConfig["groups"][id_v1]["locations"][light][0],
            "y": bridgeConfig["groups"][id_v1]["locations"][light][1],
            "z": bridgeConfig["groups"][id_v1]["locations"][light][2]
          },
          "service": {
            "reference_id": entertainmentUuid,
            "reference_type": "entertainment",
            "rid": entertainmentUuid,
            "rtype": "entertainment"
          }
        })
        index += 1
    return result

def buildV2Bridge():
    return {
        "bridge_id": bridgeConfig["config"]["bridgeid"].lower(),
        "id": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["uuid"],
        "id_v1": "",
        "type": "bridge"
    }

def buildV2Device(uuid):
    id_v1 = bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["id_v1"]
    result = {"id": uuid, "type": "device"}
    if id_v1 == "":
        result["id_v1"] = ""
        result["metadata"] = {
            "archetype": "bridge_v2",
            "name": bridgeConfig["config"]["name"]
        }
        result["product_data"] = {
            "certified": True,
            "manufacturer_name": "Signify Netherlands B.V.",
            "model_id": "BSB002",
            "product_archetype": "bridge_v2",
            "product_name": "Philips hue",
            "software_version": "1.41.1941132080"
        }
        result["services"] = [
            {
              "reference_id": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["uuid"],
              "reference_type": "bridge",
              "rid": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["uuid"],
              "rtype": "bridge"
            },
            {
              "reference_id": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["zigbee_connectivity"],
              "reference_type": "zigbee_connectivity",
              "rid": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["zigbee_connectivity"],
              "rtype": "zigbee_connectivity"
            },
            {
              "reference_id": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["entertainment"],
              "reference_type": "entertainment",
              "rid": bridgeConfig["emulator"]["links"]["v2"]["bridge"]["entertainment"],
              "rtype": "entertainment"
            }
        ]
    elif bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["resource"] == "lights":
        result["metadata"] = {
            "archetype": "sultan_bulb",
            "name": bridgeConfig["lights"][id_v1]["name"]
        }
        result["product_data"] = {
            "certified": True,
            "manufacturer_name": "Signify Netherlands B.V.",
            "model_id": bridgeConfig["lights"][id_v1]["modelid"],
            "product_archetype": "sultan_bulb",
            "product_name": "Hue color lamp",
            "software_version": "1.65.9"
            }
        result["services"] = [
        {
          "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["lightUuid"],
          "reference_type": "light",
          "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["lightUuid"],
          "rtype": "light"
        },
        {
          "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["zigbee_connectivity"],
          "reference_type": "zigbee_connectivity",
          "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["zigbee_connectivity"],
          "rtype": "zigbee_connectivity"
        },
        {
          "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["entertianmentUuid"],
          "reference_type": "entertainment",
          "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["entertianmentUuid"],
          "rtype": "entertainment"
        }
        ]
    elif bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["resource"] == "sensors":
        if bridgeConfig["sensors"][id_v1]["modelid"] == "SML001":
            result["metadata"] = {
                "archetype": "unknown_archetype",
                "name": bridgeConfig["sensors"][id_v1]["name"]
            }
            result["product_data"] = {
                "certified": True,
                "manufacturer_name": "Signify Netherlands B.V.",
                "model_id": "SML001",
                "product_archetype": "unknown_archetype",
                "product_name": "Hue motion sensor",
                "software_version": "1.1.27575"
            }
            result["services"] = [
                {
                  "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["motionUuId"],
                  "reference_type": "motion",
                  "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["motionUuId"],
                  "rtype": "motion"
                },
                {
                  "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["batteryUuid"],
                  "reference_type": "battery",
                  "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["batteryUuid"],
                  "rtype": "battery"
                },
                {
                  "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["zigBeeUuid"],
                  "reference_type": "zigbee_connectivity",
                  "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["zigBeeUuid"],
                  "rtype": "zigbee_connectivity"
                },
                {
                  "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["lightUuid"],
                  "reference_type": "light_level",
                  "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["lightUuid"],
                  "rtype": "light_level"
                },
                {
                  "reference_id": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["temperatureUuid"],
                  "reference_type": "temperature",
                  "rid": bridgeConfig["emulator"]["links"]["v2"]["device"][uuid]["temperatureUuid"],
                  "rtype": "temperature"
                }
            ]


    return result

class AuthV1(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" in authorisation:
            return {}, 200, {'hue-application-id': '36b1e193-4b74-4763-a054-0578cd927a7b'}
        else:
            return "", 401

class ClipV2(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        data = []
        for key in bridgeConfig["emulator"]["links"]["v2"]["scene"].keys():
            data.append(buildV2Scene(key))
        for key in bridgeConfig["emulator"]["links"]["v2"]["light"].keys():
            data.append(buildV2Light(key))
        for key in bridgeConfig["emulator"]["links"]["v2"]["room"].keys():
            data.append(buildV2Room(key))
        for key in bridgeConfig["emulator"]["links"]["v2"]["groupedLights"].keys():
            data.append(buildV2GroupedLight(key))
        for key in bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"].keys():
            data.append(buildV2ZigBeeConnect(key))
        for key in bridgeConfig["emulator"]["links"]["v2"]["entertainment"].keys():
            data.append(buildV2Entertainment(key))
        for key in bridgeConfig["emulator"]["links"]["v2"]["entertainment_configuration"].keys():
            data.append(buildV2EntertainmentConfig(key))
        for key in bridgeConfig["emulator"]["links"]["v2"]["device"].keys():
            data.append(buildV2Device(key))
        data.append(buildV2Bridge())
        return {"errors": [], "data": data}

class ClipV2Resource(Resource):
    def get(self, resource):
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        data = []
        if resource == "scene":
            for key in bridgeConfig["emulator"]["links"]["v2"]["scene"].keys():
                data.append(buildV2Scene(key))
        elif resource == "light":
            for key in bridgeConfig["emulator"]["links"]["v2"]["light"].keys():
                data.append(buildV2Light(key))
        elif resource == "room":
            for key in bridgeConfig["emulator"]["links"]["v2"]["room"].keys():
                data.append(buildV2Room(key))
        elif resource == "grouped_light":
            for key in bridgeConfig["emulator"]["links"]["v2"]["groupedLights"].keys():
                data.append(buildV2GroupedLight(key))
        elif resource == "zigbee_connectivity":
            for key in bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"].keys():
                data.append(buildV2ZigBeeConnect(key))
        elif resource == "entertainment":
            for key in bridgeConfig["emulator"]["links"]["v2"]["entertainment"].keys():
                data.append(buildV2Entertainment(key))
        elif resource == "entertainment_configuration":
            for key in bridgeConfig["emulator"]["links"]["v2"]["entertainment_configuration"].keys():
                data.append(buildV2EntertainmentConfig(key))
        elif resource == "device":
            for key in bridgeConfig["emulator"]["links"]["v2"]["device"].keys():
                data.append(buildV2Device(key))
        elif resource == "bridge":
            data.append(buildV2Bridge())
        return {"errors": [], "data": data}

class ClipV2ResourceId(Resource):
    def get(self, resource, resourceid):
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        if resource == "scene":
            if resourceid in bridgeConfig["emulator"]["links"]["v2"]["scene"]:
                return {"errors": [], "data": [buildV2Scene(resourceid)]}
        elif resource == "light":
            if resourceid in bridgeConfig["emulator"]["links"]["v2"]["light"]:
                return {"errors": [], "data": [buildV2Light(resourceid)]}
        elif resource == "room":
            if resourceid in bridgeConfig["emulator"]["links"]["v2"]["room"]:
                return {"errors": [], "data": [buildV2Room(resourceid)]}
        elif resource == "grouped_light":
            if resourceid in bridgeConfig["emulator"]["links"]["v2"]["groupedLights"]:
                return {"errors": [], "data": [buildV2GroupedLight(resourceid)]}
        elif resource == "zigbee_connectivity":
            if resourceid in bridgeConfig["emulator"]["links"]["v2"]["zigbee_connectivity"]:
                return {"errors": [], "data": [buildV2ZigBeeConnect(resourceid)]}
        elif resource == "entertainment":
            if resourceid in bridgeConfig["emulator"]["links"]["v2"]["entertainment"]:
                return {"errors": [], "data": [buildV2Entertainment(resourceid)]}
        elif resource == "entertainment_configuration":
            if resourceid in bridgeConfig["emulator"]["links"]["v2"]["entertainment_configuration"]:
                return {"errors": [], "data": [buildV2EntertainmentConfig(resourceid)]}
        elif resource == "bridge":
            return {"errors": [], "data": [buildV2Bridge()]}


    def put(self, resource, resourceid):
        print("####PUT")
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        putDict = request.get_json(force=True)
        if resource == "light":
            v1Request = {}
            if "dimming" in putDict:
                v1Request["bri"] = putDict["dimming"]["brightness"]
            if "on" in putDict:
                v1Request["on"] =  putDict["on"]["on"]
            if "color" in putDict:
                if "xy" in putDict["color"]:
                    v1Request["xy"] = [putDict["color"]["xy"]["x"], putDict["color"]["xy"]["y"]]
                v1Request["on"] =  putDict["on"]["on"]
            sendLightRequest(bridgeConfig["emulator"]["links"]["v2"]["light"][resourceid]["id_v1"], v1Request)
        elif resource == "entertainment_configuration":
            id_v1 = bridgeConfig["emulator"]["links"]["v2"]["entertainment_configuration"][resourceid]["id_v1"]
            if "action" in putDict:
                if putDict["action"] == "start":
                    bridgeConfig["groups"][id_v1]["stream"]["active"] = True
                    print("start entertainment")
                    Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + authorisation["user"] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                elif putDict["action"] == "stop":
                    bridgeConfig["groups"][id_v1]["stream"]["active"] = False
                    Popen(["killall", "entertain-srv"])
                    print("stop entertainment")
        return {"data": [{
            "reference_id": resourceid,
            "reference_type": "light",
            "rid": resourceid,
            "rtype": "light"
            }]}


    def post(self, resource, resourceid):
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        putDict = request.get_json(force=True)
        return {"ok"}
