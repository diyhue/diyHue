import configManager
import logManager
from HueObjects import Group, EntertainmentConfiguration, Scene, BehaviorInstance, GeofenceClient, SmartScene, StreamEvent, Device
import uuid
import json
import weakref
from subprocess import Popen
from flask_restful import Resource
from flask import request
from services.entertainment import entertainmentService
from threading import Thread
from time import sleep
from functions.core import nextFreeId, bridgeIdentity
from functions.motionAware import (
    createMotionAwareArea,
    deleteMotionAwareArea,
    isMotionAwareCandidateDevice,
    updateMotionAwareResource,
    v2MotionAreaCandidateService,
    v2MotionAwareResources,
)
from motionAwareConfig import (
    MOTION_AREA_CONFIGURATION,
    SERVED_MOTION_RESOURCE_TYPES,
)
from datetime import datetime, timezone
from functions.scripts import behaviorScripts
from lights.discover import scanForLights
from functions.daylightSensor import daylightSensor

logging = logManager.logger.get_logger(__name__)

bridgeConfig = configManager.bridgeConfig.yaml_config


def _identifyMotionAwareLight(device):
    """Execute the V2 identify action through the existing light interface.

    MQTT lights that explicitly advertise a ``blink`` effect get the native
    one-shot effect; all other protocols retain the standard Hue ``select``
    alert fallback.  No protocol-specific transport is introduced here.
    """
    light = device.firstElement() if hasattr(device, "firstElement") else device
    protocol_cfg = getattr(light, "protocol_cfg", {})
    capabilities = protocol_cfg.get("z2m_capabilities", {}) if isinstance(protocol_cfg, dict) else {}
    effects = capabilities.get("effect_list", []) if isinstance(capabilities, dict) else []
    command = {"effect": "blink"} if (
        getattr(light, "protocol", None) == "mqtt" and "blink" in effects
    ) else {"alert": "select"}
    light.setV1State(command)
    logging.info(
        "MOTION_IDENTIFY light=%s protocol=%s action=%s",
        getattr(light, "id_v1", "unknown"),
        getattr(light, "protocol", "unknown"),
        command,
    )

PRO_MOTION_RESOURCE_TYPES = SERVED_MOTION_RESOURCE_TYPES

# Resource types reported by the `clip` capability resource on a
# live BSB003 Hue Bridge Pro.
#
# `motion_area_candidate` is deliberately absent: Bridge Pro uses it
# only as a ResourceIdentifier rtype on compatible device services and
# MotionAware participants; it is not a served resource collection.
PRO_CAPABILITY_RESOURCES = [
    "motion_area_configuration",
    "convenience_area_motion",
    "security_area_motion",
    "entertainment_configuration",
    "bridge",
    "button",
    "device",
    "device_power",
    "device_software_update",
    "entertainment",
    "light",
    "light_level",
    "zigbee_connectivity",
    "zgp_connectivity",
    "motion",
    "camera_motion",
    "relative_rotary",
    "temperature",
    "zigbee_device_discovery",
    "contact",
    "tamper",
    "speaker",
    "bell_button",
    "switch_input_configuration",
    "bridge_home",
    "grouped_light",
    "grouped_light_level",
    "grouped_motion",
    "room",
    "service_group",
    "zone",
    "scene",
    "matter",
    "matter_fabric",
    "behavior_script",
    "behavior_instance",
    "geofence_client",
    "geolocation",
    "smart_scene",
    "clip",
]

# Bridge Pro resource types that diyHue does not implement yet. They are
# valid served collections in Pro mode, but remain empty until their
# corresponding emulation is implemented.
PRO_EMPTY_RESOURCE_TYPES = (
    "device_software_update",
    "zgp_connectivity",
    "camera_motion",
    "speaker",
    "bell_button",
    "switch_input_configuration",
    "grouped_light_level",
    "grouped_motion",
    "service_group",
    "matter",
    "matter_fabric",
)

v2Resources = {"light": {}, "scene": {}, "smart_scene": {}, "grouped_light": {}, "room": {}, "zone": {
}, "entertainment": {}, "entertainment_configuration": {}, "zigbee_connectivity": {}, "zigbee_device_discovery": {}, "device_power": {},
"geofence_client": {}, "motion": {}, "light_level": {}, "temperature": {}, "relative_rotary": {}, "button": {}, "contact": {}, "tamper": {}}


def getObject(element, v2uuid):
    if element == "behavior_instance":
        return bridgeConfig[element][v2uuid]
    elif element == "device":
        # Device.id_v2 is derived again when its first service is attached.
        # Older configs (and newly-created V1 devices) can therefore retain
        # the pre-service UUID as the dictionary key while the V2 API exposes
        # the derived UUID. Resolve the advertised UUID as well as the key.
        if v2uuid in bridgeConfig[element]:
            return bridgeConfig[element][v2uuid]
        for device in bridgeConfig[element].values():
            if device.id_v2 == v2uuid:
                return device
        raise KeyError(v2uuid)
    elif element in v2Resources and v2uuid in v2Resources[element]:
        logging.debug("Cache Hit for " + element)
        return v2Resources[element][v2uuid]()
    elif element in ["light", "scene", "grouped_light", "smart_scene"]:
        for v1Element in ["lights", "groups", "scenes", "smart_scene"]:
            for key, obj in bridgeConfig[v1Element].items():
                if obj.id_v2 == v2uuid:
                    v2Resources[element][v2uuid] = weakref.ref(obj)
                    logging.debug("Cache Miss " + element)
                    return obj
    elif element in ["entertainment", "zigbee_connectivity", "motion", "light_level", "temperature", "relative_rotary", "button", "tamper", "contact"]:
        for key, obj in bridgeConfig["device"].items():
            if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2 + element)) == v2uuid:
                v2Resources[element][v2uuid] = weakref.ref(obj)
                return obj
    else:
        for v1Element in ["lights", "groups", "scenes", "sensors", "geofence_clients"]:
            for key, obj in bridgeConfig[v1Element].items():
                if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2 + element)) == v2uuid:
                    logging.debug("Cache Miss " + element)
                    v2Resources[element][v2uuid] = weakref.ref(obj)
                    return obj
    logging.info("element not found!")
    return False


def authorizeV2(headers):
    if "hue-application-key" in headers and headers["hue-application-key"] in bridgeConfig["apiUsers"]:
        bridgeConfig["apiUsers"][headers["hue-application-key"]
                                 ].last_use_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        return {"user": bridgeConfig["apiUsers"][headers["hue-application-key"]]}
    return []

def v2BridgeEntertainment():
    return {"id": "57a9ebc9-406d-4a29-a4ff-42acee9e9be7",
            "owner": {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'device')),
                "rtype": "device"
                },
            "renderer": False,
            "proxy": True,
            "equalizer": False,
            "max_streams": 1,
            "type": "entertainment"
            }



def v2HomeKit():
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'homekit')),
            "status": "unpaired",
            "status_values": [
                "pairing",
                "paired",
                "unpaired"
            ],
        "type": "homekit"
    }


def v2BridgeZigBee():
    return {"id": str(uuid.uuid5(
        uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity')),
            "owner": {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'device')),
                "rtype": "device"
                },
            "status": "connected",
            "mac_address": bridgeConfig["config"]["mac"][:8] + ":01:01:" +  bridgeConfig["config"]["mac"][9:],
            "channel": {
                "value": "channel_25",
                "status": "set"
                },
            "type": "zigbee_connectivity"
            }

def v2BridgeZigBeeDiscovery():
    return{"id": str(uuid.uuid5(
        uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'zigbee_device_discovery')),
        "owner": {
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'device')),
            "rtype": "device"
        },
        "action": {
            "action_type_values": [
                "search"
            ]
        },
        "status": bridgeConfig["config"]["zigbee_device_discovery_info"]["status"],
        "type": "zigbee_device_discovery",
        }


def v2GeofenceClient():
    user = authorizeV2(request.headers)
    result = {
      "id": str(uuid.uuid5(uuid.NAMESPACE_URL, request.headers["hue-application-key"])),
      "name": user["user"].name,
      "type": "geofence_client"
    }
    return result

def v2Bridge():
    bridge_id = bridgeConfig["config"]["bridgeid"]
    return {
        "bridge_id": bridge_id.lower(),
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridge_id + 'bridge')),
        "id_v1": "",
        "owner": {"rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridge_id + 'device')), "rtype": "device"},
        "time_zone": {"time_zone": bridgeConfig["config"]["timezone"]},
        "type": "bridge"
    }

def v2BridgeHome():
    result = {}
    result["children"] = []
    result["children"].append({"rid": v2Bridge()["id"], "rtype": "device"}) # the bridge
    
    result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                  bridgeConfig["groups"]["0"].id_v2 + 'bridge_home'))
    result["id_v1"] = "/groups/0"
    for key, device in bridgeConfig["device"].items():
        result["children"].append({"rid": device.id_v2, "rtype": "device"})
    for key, group in bridgeConfig["groups"].items():
        if group.type == "Room":
            result["children"].append({"rid": group.getV2Room()["id"], "rtype": "room"})
    result["services"] = []
    result["services"].append({"rid": bridgeConfig["groups"]["0"].id_v2 ,"rtype": "grouped_light"})
    result["type"] = "bridge_home"
    return result

def geoLocation():
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'geolocation')),
        "is_configured": bridgeConfig["sensors"]["1"].config["configured"],
        "sun_today": {
            "sunset_time": bridgeConfig["sensors"]["1"].config["sunset"] if "lat" in bridgeConfig["sensors"]["1"].protocol_cfg else "",
            "day_type": "normal_day"
        },
        "type": "geolocation"
    }




def v2Device(device):
    """Return a V2 device with Bridge Pro-only services when applicable."""
    result = device.getDevice()

    if isMotionAwareCandidateDevice(device):
        candidate = v2MotionAreaCandidateService(device)

        if candidate not in result["services"]:
            result["services"].append(candidate)

    return result
















def v2Clip():
    config = bridgeConfig["config"]

    if bridgeIdentity(config)["profile"] != "pro":
        return None

    return {
        "id": str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            config["bridgeid"] + "clip"
        )),
        "resources": PRO_CAPABILITY_RESOURCES.copy(),
        "type": "clip"
    }


def v2BridgeDevice():
    config = bridgeConfig["config"]
    identity = bridgeIdentity(config)
    bridge_id = config["bridgeid"]
    result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridge_id + 'device')), "type": "device"}
    result["id_v1"] = ""
    result["metadata"] = {"archetype": identity["archetype"], "name": config["name"]}
    result["identify"] = {}
    if identity["profile"] == "pro":
        software_version = identity["software_version"]
    else:
        # Preserve the existing classic Bridge V2 conversion.
        swversion_str = config["swversion"]
        if len(swversion_str) == 10:
            software_version = (
                f"{swversion_str[0]}."
                f"{swversion_str[1:3]}."
                f"{swversion_str[3:]}"
            )
        else:
            software_version = swversion_str
    result["product_data"] = {
        "certified": True,
        "manufacturer_name": "Signify Netherlands B.V.",
        "model_id": identity["modelid"],
        "product_archetype": identity["archetype"],
        "product_name": identity["product_name"],
        "software_version": software_version
    }
    if identity["profile"] == "pro":
        service_specs = [
            ("bridge", "bridge"),
            ("entertainment", "entertainment"),
            (
                "zigbee_device_discovery",
                "zigbee_device_discovery"
            )
        ]
    else:
        service_specs = [
            ("bridge", "bridge"),
            ("zigbee_connectivity", "zigbee_connectivity"),
            (
                "zigbee_device_discovery",
                "zigbee_device_discovery"
            ),
            ("entertainment", "entertainment")
        ]

    result["services"] = [
        {
            "rid": str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                bridge_id + suffix
            )),
            "rtype": resource_type
        }
        for suffix, resource_type in service_specs
    ]
    return result

def v2DiyHueBridge():
    bridge_id = bridgeConfig["config"]["bridgeid"]
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridge_id + 'diyhue')),
        "id_v1": "",
        "owner": {"rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridge_id + 'device')), "rtype": "device"},
        "type": "diyhue",
        "hue_essentials_key": bridgeConfig["config"]["Hue Essentials key"], 
        "remote_api_enabled": bridgeConfig["config"]["Remote API enabled"],
        "remote_discovery": bridgeConfig["config"]["discovery"]
    }

class AuthV1(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" in authorisation:
            logging.debug("Auth 200")
            return {}, 200, {'hue-application-id': request.headers["hue-application-key"]}

        else:
            logging.info("Auth 403")
            return '', 403


class ClipV2(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        data = []
        # homekit
        data.append(v2HomeKit())
        # device
        data.append(v2BridgeDevice())
        for key, device in bridgeConfig["device"].items():
            data.append(v2Device(device))
        # bridge
        data.append(v2Bridge())
        data.append(v2DiyHueBridge())

        clip = v2Clip()
        if clip is not None:
            data.append(clip)

        motion_aware = v2MotionAwareResources()
        for resource_type in PRO_MOTION_RESOURCE_TYPES:
            data.extend(motion_aware[resource_type])

        # zigbee
        data.append(v2BridgeZigBee())
        for key, device in bridgeConfig["device"].items():
            data.append(device.getZigBee())
        data.append(v2BridgeZigBeeDiscovery())
        # entertainment
        data.append(v2BridgeEntertainment())
        for key, device in bridgeConfig["device"].items():
            entertainment = device.getV2Entertainment()
            if entertainment != None:
                data.append(entertainment)
        # scenes
        for key, scene in bridgeConfig["scenes"].items():
            data.append(scene.getV2Api())
        # smart_scene
        for key, smartscene in bridgeConfig["smart_scene"].items():
            data.append(smartscene.getV2Api())
        # lights
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getV2Api())
        # room
        for key, group in bridgeConfig["groups"].items():
            if group.type == "Room":
                data.append(group.getV2Room())
            elif group.type == "Zone":
                data.append(group.getV2Zone())
        # behavior_instance
        for key, instance in bridgeConfig["behavior_instance"].items():
            data.append(instance.getV2Api())
        # entertainment_configuration
        for key, group in bridgeConfig["groups"].items():
            if group.type == "Entertainment":
                data.append(group.getV2Api())
        # group
            else:
                data.append(group.getV2GroupedLight())
        # bridge home
        data.append(v2BridgeHome())
        data.append(v2GeofenceClient())
        data.append(geoLocation())
        for script in behaviorScripts():
            data.append(script)
        for key, device in bridgeConfig["device"].items():
            motion = device.getMotion()
            if motion != None:
                data.append(motion)
            buttons = device.getButtons()
            if len(buttons) != 0:
                for button in buttons:
                    data.append(button)
            power = device.getDevicePower()
            if power != None:
                data.append(power)
            rotarys = device.getRotary()
            if len(rotarys) != 0:
                for rotary in rotarys:
                    data.append(rotary)
            temperature = device.getTemperature()
            if temperature != None:
                data.append(temperature)
            lightlevel = device.getLightLevel()
            if lightlevel != None:
                data.append(lightlevel)
            contact = device.getContact()
            if contact != None:
                data.append(contact)
            tamper = device.getTamper()
            if tamper != None:
                data.append(tamper)

        return {"errors": [], "data": data}


class ClipV2Resource(Resource):
    def get(self, resource):
        # logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        response = {"data": [], "errors": []}
        if resource == "scene":
            for key, scene in bridgeConfig["scenes"].items():
                response["data"].append(scene.getV2Api())
        elif resource == "smart_scene":
            for key, smartscene in bridgeConfig["smart_scene"].items():
                response["data"].append(smartscene.getV2Api())
        elif resource == "light":
            for key, light in bridgeConfig["lights"].items():
                response["data"].append(light.getV2Api())
        elif resource == "room":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Room":
                    response["data"].append(group.getV2Room())
        elif resource == "zone":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Zone":
                    response["data"].append(group.getV2Zone())
        elif resource == "grouped_light":
            for key, group in bridgeConfig["groups"].items():
                response["data"].append(group.getV2GroupedLight())
        elif resource == "zigbee_connectivity":
            for key, light in bridgeConfig["lights"].items():
                zigbee = light.getZigBee()
                if zigbee != None:
                    response["data"].append(zigbee)
            for key, sensor in bridgeConfig["sensors"].items():
                zigbee = sensor.getZigBee()
                if zigbee != None:
                    response["data"].append(zigbee)
            response["data"].append(v2BridgeZigBee())  # the bridge
        elif resource == "entertainment":
            for key, light in bridgeConfig["lights"].items():
                response["data"].append(light.getV2Entertainment())
            response["data"].append(v2BridgeEntertainment())
        elif resource == "entertainment_configuration":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Entertainment":
                    response["data"].append(group.getV2Api())
        elif resource == "device":
            for key, device in bridgeConfig["device"].items():
                response["data"].append(v2Device(device))
            response["data"].append(v2BridgeDevice())  # the bridge
        elif resource == "zigbee_device_discovery":
            response["data"].append(v2BridgeZigBeeDiscovery())
        elif resource == "bridge":
            response["data"].append(v2Bridge())
        elif resource == "diyhue":
            response["data"].append(v2DiyHueBridge())
        elif resource == "bridge_home":
            response["data"].append(v2BridgeHome())
        elif resource == "homekit":
            response["data"].append(v2HomeKit())
        elif resource == "geolocation":
            response["data"].append(geoLocation())
        elif (
            resource == "clip"
            and bridgeIdentity(bridgeConfig["config"])["profile"] == "pro"
        ):
            response["data"].append(v2Clip())
        elif (
            resource in PRO_MOTION_RESOURCE_TYPES
            and bridgeIdentity(bridgeConfig["config"])["profile"] == "pro"
        ):
            response["data"].extend(
                v2MotionAwareResources()[resource]
            )
        elif (
            resource in PRO_EMPTY_RESOURCE_TYPES
            and bridgeIdentity(bridgeConfig["config"])["profile"] == "pro"
        ):
            # Valid Bridge Pro collections whose emulation is not yet
            # implemented. An empty collection is preferable to
            # advertising a capability and then returning Not Found.
            pass
        elif resource == "behavior_instance":
            for key, instance in bridgeConfig["behavior_instance"].items():
                response["data"].append(instance.getV2Api())
        elif resource == "geofence_client":
            response["data"].append(v2GeofenceClient())
        elif resource == "behavior_script":
            for script in behaviorScripts():
                response["data"].append(script)
        elif resource == "motion":
            for key, device in bridgeConfig["device"].items():
                motion = device.getMotion()
                if motion != None:
                    response["data"].append(motion)
        elif resource == "device_power":
            for key, device in bridgeConfig["device"].items():
                power = device.getDevicePower()
                if power != None:
                    response["data"].append(power)
        elif resource == "button":
            for key, device in bridgeConfig["device"].items():
                buttons = device.getButtons()
                if len(buttons) != 0:
                    for button in buttons:
                        response["data"].append(button)
        elif resource == "relative_rotary":
            for key, device in bridgeConfig["device"].items():
                rotarys = device.getRotary()
                if len(rotarys) != 0:
                    for rotary in rotarys:
                        response["data"].append(rotary)
        elif resource == "temperature":
            for key, device in bridgeConfig["device"].items():
                temperature = device.getTemperature()
                if temperature != None:
                    response["data"].append(temperature)
        elif resource == "light_level":
            for key, device in bridgeConfig["device"].items():
                lightlevel = device.getLightLevel()
                if lightlevel != None:
                    response["data"].append(lightlevel)
        elif resource == "contact":
            for key, device in bridgeConfig["device"].items():
                contact = device.getContact()
                if contact != None:
                    response["data"].append(contact)
        elif resource == "tamper":
            for key, device in bridgeConfig["device"].items():
                tamper = device.getTamper()
                if tamper != None:
                    response["data"].append(tamper)
        else:
            response["errors"].append({"description": "Not Found"})
            del response["data"]

        return response

    def post(self, resource):
        # logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        postDict = request.get_json(force=True)
        logging.info(postDict)
        newObject = None
        if resource == MOTION_AREA_CONFIGURATION:
            try:
                created = createMotionAwareArea(postDict)
            except ValueError as error:
                return {
                    "data": [],
                    "errors": [{"description": str(error)}]
                }, 400

            if created is None:
                return {
                    "data": [],
                    "errors": [{"description": "MotionAware is unavailable"}]
                }, 404

            return {
                "data": [{
                    **created,
                    "rid": created["id"],
                    "rtype": resource
                }],
                "errors": []
            }, 201
        elif resource == "scene":
            new_object_id = nextFreeId(bridgeConfig, "scenes")
            objCreation = {
                "id_v1": new_object_id,
                "name": postDict["metadata"]["name"],
                "image": postDict["metadata"]["image"]["rid"] if "image" in postDict["metadata"] else None,
                "owner": bridgeConfig["apiUsers"][request.headers["hue-application-key"]],
            }
            if "group" in postDict:
                objCreation["group"] = weakref.ref(
                    getObject(postDict["group"]["rtype"], postDict["group"]["rid"]))
                objCreation["type"] = "GroupScene"
                del postDict["group"]
            elif "lights" in postDict:
                objCreation["type"] = "LightScene"
                objLights = []
                for light in postDict["lights"]:
                    objLights.append(getObject(light["rtype"], light["rid"]))
                objCreation["lights"] = objLights
            objCreation.update(postDict)
            newObject = Scene.Scene(objCreation)
            bridgeConfig["scenes"][new_object_id] = newObject
            if "actions" in postDict:
                for action in postDict["actions"]:
                    if "target" in action:
                        if action["target"]["rtype"] == "light":
                            lightObj = getObject(
                                "light",  action["target"]["rid"])
                            sceneState = {}
                            scene = action["action"]
                            if "on" in scene:
                                sceneState["on"] = scene["on"]["on"]
                            if "dimming" in scene:
                                sceneState["bri"] = int(
                                    scene["dimming"]["brightness"] * 2.54)
                            if "color" in scene:
                                if "xy" in scene["color"]:
                                    sceneState["xy"] = [
                                        scene["color"]["xy"]["x"], scene["color"]["xy"]["y"]]
                            if "color_temperature" in scene:
                                if "mirek" in scene["color_temperature"]:
                                    sceneState["ct"] = scene["color_temperature"]["mirek"]
                            if "gradient" in scene:
                                sceneState["gradient"] = scene["gradient"]
                            newObject.lightstates[lightObj] = sceneState
        elif resource == "smart_scene":
            new_object_id = nextFreeId(bridgeConfig, "smart_scene")
            objCreation = {
                "id_v1": new_object_id,
                "name": postDict["metadata"]["name"],
                "image": postDict["metadata"]["image"]["rid"] if "image" in postDict["metadata"] else None,
                "action": postDict["recall"]["action"],
                "timeslots": postDict["week_timeslots"][0]["timeslots"],
                "recurrence": postDict["week_timeslots"][0]["recurrence"]
            }
            del postDict["week_timeslots"]
            objCreation.update(postDict)
            newObject = SmartScene.SmartScene(objCreation)
            bridgeConfig["smart_scene"][new_object_id] = newObject
        elif resource == "behavior_instance":
            newObject = BehaviorInstance.BehaviorInstance(postDict)
            bridgeConfig["behavior_instance"][newObject.id_v2] = newObject
        elif resource == "entertainment_configuration":
            new_object_id = nextFreeId(bridgeConfig, "groups")
            objCreation = {
                "id_v1": new_object_id,
                "name": postDict["metadata"]["name"]
            }
            objCreation.update(postDict)
            newObject = EntertainmentConfiguration.EntertainmentConfiguration(objCreation)
            if "locations" in postDict:
                if "service_locations" in postDict["locations"]:
                    for element in postDict["locations"]["service_locations"]:
                        obj = getObject(
                            element["service"]["rtype"], element["service"]["rid"])
                        newObject.add_light(obj)
                        newObject.locations[obj] = element["positions"]
            bridgeConfig["groups"][new_object_id] = newObject
        elif resource in ["room", "zone"]:
            new_object_id = nextFreeId(bridgeConfig, "groups")
            objCreation = {
                "id_v1": new_object_id,
                "name": postDict["metadata"]["name"],
            }
            objCreation["type"] = "Room" if resource == "room" else "Zone"
            logging.debug(f"Before update: objCreation={objCreation}")
            objCreation.update(postDict)
            logging.debug(f"After update: objCreation={objCreation}")
            # Ensure archetype is properly mapped to icon_class after update
            if "metadata" in objCreation and "archetype" in objCreation["metadata"]:
                objCreation["class"] = objCreation["metadata"]["archetype"]
                logging.debug(f"Setting class to: {objCreation['class']} from archetype: {objCreation['metadata']['archetype']}")
            else:
                logging.warning(f"No archetype found in metadata: {objCreation.get('metadata', {})}")
            logging.debug(f"Final objCreation before Group creation: {objCreation}")
            # Mark this group as created via V2 API to prevent duplicate events
            objCreation["_skip_stream_event"] = True
            newObject = Group.Group(objCreation)
            if "children" in postDict:
                for children in postDict["children"]:
                    obj = getObject(
                        children["rtype"], children["rid"])
                    newObject.add_light(obj)

            bridgeConfig["groups"][new_object_id] = newObject
            
            # Create a combined event message with both room/zone creation and bridge_home update
            element_type = "room" if newObject.type == "Room" else "zone"
            logging.debug(f"Creating combined event message for {element_type} creation and bridge_home update")
            try:
                # Get the bridge_home update data
                bridge_home_data = None
                if "groups" in bridgeConfig and "0" in bridgeConfig["groups"] and bridgeConfig["groups"]["0"] is not None:
                    bridge_home_data = {
                        "creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "data": [{"children": [], "id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["groups"]["0"].id_v2 + 'bridge_home')), "id_v1": "/groups/0", "type": "bridge_home"}],
                        "id": str(uuid.uuid4()),
                        "type": "update"
                    }
                    
                    # Add only the newly created room/zone to children (not all existing ones)
                    if newObject.type == "Room":
                        bridge_home_data["data"][0]["children"].append({"rid": newObject.getV2Room()["id"], "rtype": "room"})
                    elif newObject.type == "Zone":
                        bridge_home_data["data"][0]["children"].append({"rid": newObject.getV2Zone()["id"], "rtype": "zone"})
                    
                    # Add the bridge itself as a device (this is what the original bridge does)
                    # The bridge should be represented as a device in the children list
                    bridge_device_id = str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["groups"]["0"].id_v2 + 'bridge_device'))
                    bridge_home_data["data"][0]["children"].append({"rid": bridge_device_id, "rtype": "device"})
                    
                    logging.debug(f"Bridge_home update: 1 new {element_type} + 1 bridge device")
                
                # Create combined event message
                if bridge_home_data:
                    # Get the appropriate V2 API data based on type
                    v2_data = newObject.getV2Room() if newObject.type == "Room" else newObject.getV2Zone()
                    combined_message = [
                        {
                            "creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "data": [v2_data],
                            "id": str(uuid.uuid4()),
                            "type": "add"
                        },
                        bridge_home_data
                    ]
                    
                    # Send the combined message through the shared event stream
                    # so all connected clients can consume it independently.
                    StreamEvent(combined_message)
                    logging.debug(f"Combined event message sent successfully")
                else:
                    logging.warning("Could not create bridge_home data, falling back to separate events")
                    # Fallback to separate events if bridge_home is not available
                    from flaskUI.restful import GroupZeroMessage
                    GroupZeroMessage()
                    
            except Exception as e:
                logging.error(f"Failed to create combined event message: {e}")
                # Fallback to separate events
                try:
                    from flaskUI.restful import GroupZeroMessage
                    GroupZeroMessage()
                except Exception as e2:
                    logging.error(f"Fallback also failed: {e2}")
        elif resource == 'geofence_client':
            new_object_id = nextFreeId(bridgeConfig, "geofence_clients")
            objCreation = {
                "id_v1": new_object_id,
                "name": postDict["name"],
                "type": "geofence_client",
                "is_at_home": postDict.get("is_at_home", False)
            }
            newObject = GeofenceClient.GeofenceClient(objCreation)
            bridgeConfig["geofence_clients"][new_object_id] = newObject
        else:
            return {
                "errors": [{
                    "description": f"Resource type not supported: {resource}"
                }]
            }, 500

        # return message
        if resource == "room":
            # For rooms, return the room ID (not the grouped_light ID)
            rid = str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + 'room'))
        elif resource == "zone":
            # For zones, return the zone ID (not the grouped_light ID)
            rid = str(uuid.uuid5(uuid.NAMESPACE_URL, newObject.id_v2 + 'zone'))
        else:
            # For other resources, use the object's V2 ID
            rid = newObject.id_v2
            
        returnMessage = {"data": [{
            "rid": rid,
            "rtype": resource}
        ], "errors": []}

        logging.debug(json.dumps(returnMessage, sort_keys=True, indent=4))
        return returnMessage


class ClipV2ResourceId(Resource):
    def get(self, resource, resourceid):
        # logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        
        # Bridge Pro capability resources are not stored in the
        # regular V1-backed object collections.
        if bridgeIdentity(bridgeConfig["config"])["profile"] == "pro":
            if resource == "clip":
                clip = v2Clip()
                if resourceid == clip["id"]:
                    return {"errors": [], "data": [clip]}
                return {"errors": [], "data": []}

            if resource in PRO_MOTION_RESOURCE_TYPES:
                for item in v2MotionAwareResources()[resource]:
                    if item["id"] == resourceid:
                        return {"errors": [], "data": [item]}

                return {"errors": [], "data": []}

            if resource in PRO_EMPTY_RESOURCE_TYPES:
                return {"errors": [], "data": []}

        # Special handling for bridge device (not stored in bridgeConfig["device"])
        if resource == "device":
            bridge_device_id = str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'device'))
            if resourceid == bridge_device_id:
                return {"errors": [], "data": [v2BridgeDevice()]}
        
        object = getObject(resource, resourceid)
        if not object:
            return {"errors": [], "data": []}

        if resource in ["scene", "light", "smart_scene"]:
            return {"errors": [], "data": [object.getV2Api()]}
        elif resource == "room":
            return {"errors": [], "data": [object.getV2Room()]}
        elif resource == "grouped_light":
            return {"errors": [], "data": [object.getV2GroupedLight()]}
        elif resource == "device":
            return {"errors": [], "data": [v2Device(object)]}
        elif resource == "zigbee_connectivity":
            return {"errors": [], "data": [object.getZigBee()]}
        elif resource == "zigbee_device_discovery":
            return {"errors": [], "data": [object.getZigBeeDiscovery()]}
        elif resource == "entertainment":
            return {"errors": [], "data": [object.getV2Entertainment()]}
        elif resource == "entertainment_configuration":
            return {"errors": [], "data": [object.getV2Api()]}
        elif resource == "bridge":
            return {"errors": [], "data": [v2Bridge()]}
        elif resource == "motion":
            return {"errors": [], "data": [object.getMotion()]}
        elif resource == "device_power":
            return {"errors": [], "data": [object.getDevicePower()]}
        elif resource == "button":
            return {"errors": [], "data": [object.getButtons()]}
        elif resource == "relative_rotary":
            return {"errors": [], "data": [object.getRotary()]}
        elif resource == "temperature":
            return {"errors": [], "data": [object.getTemperature()]}
        elif resource == "light_level":
            return {"errors": [], "data": [object.getLightLevel()]}
        elif resource == "contact":
            return {"errors": [], "data": [object.getContact()]}
        elif resource == "tamper":
            return {"errors": [], "data": [object.getTamper()]}

    def put(self, resource, resourceid):
        # Request headers contain the application key; never log them.
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        putDict = request.get_json(force=True)
        logging.info(putDict)

        if (
            resource in PRO_MOTION_RESOURCE_TYPES
            and bridgeIdentity(bridgeConfig["config"])["profile"] == "pro"
        ):
            try:
                updated = updateMotionAwareResource(
                    resource,
                    resourceid,
                    putDict
                )
            except ValueError as err:
                return {
                    "errors": [{
                        "description": str(err)
                    }]
                }, 400

            if updated is None:
                return {
                    "errors": [{
                        "description": (
                            "MotionAware resource not found: "
                            + resourceid
                        )
                    }]
                }, 404

            return {
                "data": [{
                    "rid": resourceid,
                    "rtype": resource
                }],
                "errors": []
            }

        object = getObject(resource, resourceid)
        if resource == "light":
            object.setV2State(putDict)
        elif resource == "entertainment_configuration":
            if not object:
                return {"errors": [{"description": "Entertainment configuration not found"}], "data": []}, 404
            # A layout edit must not alter channels underneath a running stream.
            edits_layout = any(key in putDict for key in ("metadata", "configuration_type", "locations"))
            if edits_layout and (object.stream["active"] or "action" in putDict):
                return {"errors": [{"description": "Stop streaming, then edit the entertainment configuration separately"}], "data": []}, 409
            try:
                changed = object.update_configuration(putDict, getObject)
            except ValueError as error:
                return {"errors": [{"description": str(error)}], "data": []}, 400
            if changed:
                # Done in the Hue app must persist the placement before success
                # is returned. Use the target branch's existing storage API.
                configManager.bridgeConfig.save_config(backup=False, resource="groups")
                object.update_attr({})  # publish the complete, saved v2 layout
            if "action" in putDict:
                if putDict["action"] == "start":
                    logging.info("start hue entertainment")
                    Thread(target=entertainmentService, args=[
                           object, authorisation["user"]]).start()
                    for light in object.lights:
                        light().update_attr({"state": {"mode": "streaming"}})
                    object.update_attr({"stream": {"active": True, "owner": authorisation["user"].username, "proxymode": "auto", "proxynode": "/bridge"}})
                    sleep(1)
                elif putDict["action"] == "stop":
                    logging.info("stop entertainment")
                    for light in object.lights:
                        light().update_attr({"state": {"mode": "homeautomation"}})
                    Popen(["killall", "openssl"])
                    object.update_attr({"stream": {"active": False}})
        elif resource == "scene":
            # Existing scenes are edited through the V2 "actions" list.
            # Previously this was handled when creating a scene but ignored
            # on PUT, so edits made in the Hue app did not update lightstates.
            if "actions" in putDict:
                lightstates = weakref.WeakKeyDictionary()

                for action in putDict["actions"]:
                    target = action.get("target", {})

                    if target.get("rtype") != "light":
                        continue

                    lightObj = getObject(
                        "light",
                        target.get("rid")
                    )

                    if not lightObj:
                        continue

                    scene = action.get("action", {})
                    sceneState = {}

                    if "on" in scene:
                        sceneState["on"] = scene["on"]["on"]

                    if "dimming" in scene:
                        sceneState["bri"] = int(
                            scene["dimming"]["brightness"] * 2.54
                        )

                    if "color" in scene:
                        if "xy" in scene["color"]:
                            sceneState["xy"] = [
                                scene["color"]["xy"]["x"],
                                scene["color"]["xy"]["y"]
                            ]

                    if "color_temperature" in scene:
                        if "mirek" in scene["color_temperature"]:
                            sceneState["ct"] = (
                                scene["color_temperature"]["mirek"]
                            )

                    if "gradient" in scene:
                        sceneState["gradient"] = scene["gradient"]

                    lightstates[lightObj] = sceneState

                object.lightstates = lightstates
                configManager.bridgeConfig.save_config(backup=False, resource="scenes")

            # Hue scene speed is 0.0..1.0. Apply it BEFORE recall
            # and propagate changes to an already running dynamic scene.
            if "speed" in putDict:
                try:
                    requested_speed = max(
                        0.0,
                        min(1.0, float(putDict["speed"]))
                    )
                    object.speed = requested_speed

                    for light_ref in object.lights:
                        light = light_ref()
                        if (
                            light
                            and light.dynamics["status"]
                                == "dynamic_palette"
                        ):
                            # diyHue's existing scene player divides by
                            # speed; treat zero as essentially stationary
                            # rather than raising ZeroDivisionError.
                            light.dynamics["speed"] = max(
                                requested_speed,
                                0.01
                            )
                except (TypeError, ValueError):
                    pass

            if "recall" in putDict:
                # Scene.activate() copies object.speed to every light.
                # Preserve API speed=0 while supplying a safe execution
                # floor to diyHue's current 30/speed implementation.
                original_speed = object.speed
                if original_speed <= 0:
                    object.speed = 0.01

                try:
                    object.activate(putDict)
                finally:
                    object.speed = original_speed

            if "palette" in putDict:
                object.palette = putDict["palette"]
            if "metadata" in putDict:
                object.name = putDict["metadata"]["name"]
                configManager.bridgeConfig.save_config(backup=False, resource="scenes")
        elif resource == "smart_scene":
            if "recall" in putDict and "action" in putDict["recall"]:
                object.activate(putDict)
            if "transition_duration" in putDict:
                object.speed = putDict["transition_duration"]
            if "week_timeslots" in putDict:
                if "timeslots" in putDict["week_timeslots"][0]:
                    object.timeslots = putDict["week_timeslots"][0]["timeslots"]
                if "recurrence" in putDict["week_timeslots"][0]:
                    object.recurrence = putDict["week_timeslots"][0]["recurrence"]
            if "metadata" in putDict:
                object.name = putDict["metadata"]["name"]
        elif resource == "grouped_light":
            object.setV2Action(putDict)
        elif resource == "geolocation":
            bridgeConfig["sensors"]["1"].protocol_cfg = {
                "lat": putDict["latitude"], "long": putDict["longitude"]}
            bridgeConfig["sensors"]["1"].config["configured"] = True
            daylightSensor(bridgeConfig["config"]["timezone"], bridgeConfig["sensors"]["1"])
        elif resource == "behavior_instance":
            object.update_attr(putDict)
        elif resource in ["room", "zone"]:
            v1Api = {}
            if "metadata" in putDict:
                if "name" in putDict["metadata"]:
                    v1Api["name"] = putDict["metadata"]["name"]
                if "archetype" in putDict["metadata"]:
                    v1Api["icon_class"] = putDict["metadata"]["archetype"].replace("_", " ").capitalize()
            if "children" in putDict:
                for children in putDict["children"]:
                    object.add_light(getObject(children["rtype"], children["rid"]))
            object.update_attr(v1Api)
        elif resource == 'geofence_client':
            attrs = {}
            if "name" in putDict:
                attrs['name'] = putDict['name']
            if 'is_at_home' in putDict:
                attrs['is_at_home'] = putDict['is_at_home']
            if hasattr(object, 'update_attr') and callable(getattr(object, 'update_attr')):
                object.update_attr(attrs)
        elif resource == "zigbee_device_discovery":
            if putDict["action"]["action_type"] == "search":
                bridgeConfig["config"]["zigbee_device_discovery_info"]["status"] = "active"
                Thread(target=scanForLights).start()
        elif resource == "device":
            if "identify" in putDict and putDict["identify"]["action"] == "identify":
                _identifyMotionAwareLight(object)
            if "metadata" in putDict:
                if "name" in putDict["metadata"]:
                    if object:
                        object.name = putDict["metadata"]["name"]
                        for element in object.elements.items():
                            element.name = putDict["metadata"]["name"]
                    elif resourceid == v2BridgeDevice()["id"]:
                        bridgeConfig["config"]["name"] = putDict["metadata"]["name"]
                        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                        "data": [{
                                            "id": resourceid,
                                            "metadata": {
                                                "name": bridgeConfig["config"]["name"]
                                                },
                                            "type": "device"
                                        }],
                                        "id": str(uuid.uuid4()),
                                        "type": "update"
                                        }
                        StreamEvent(streamMessage)
                    configManager.bridgeConfig.save_config(backup=False, resource="config")
        elif resource == "motion":
            object.setDevice("ZLLPresence", putDict)
        elif resource == "light_level":
            object.setDevice("ZLLLightLevel", putDict)
        elif resource == "temperature":
            object.setDevice("ZLLTemperature", putDict)
        elif resource == "contact":
            object.setDevice("ZLLContact", putDict)
        elif resource == "tamper":
            object.setDevice("ZLLTamper", putDict)
        else:
            return {
                "errors": [{
                    "description": f"Resource type not supported: {resource}"
                }]
            }, 500

        response = {"data": [{
            "rid": resourceid,
            "rtype": resource
        }]}

        return response

    def delete(self, resource, resourceid):
        # logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403

        if resource == MOTION_AREA_CONFIGURATION:
            if not deleteMotionAwareArea(resourceid):
                return {
                    "data": [],
                    "errors": [{"description": "MotionAware resource not found"}]
                }, 404

            return {"data": [{"rid": resourceid, "rtype": resource}], "errors": []}

        object = getObject(resource, resourceid)
        
        if resource == "device":
            for element in object.elements:
                del bridgeConfig[element.getObjectPath()["resource"]][element.getObjectPath()["id"]]

        if hasattr(object, 'getObjectPath'):
            del bridgeConfig[object.getObjectPath()["resource"]
                             ][object.getObjectPath()["id"]]
        else:
            del bridgeConfig[resource][resourceid]

        response = {"data": [{
            "rid": resourceid,
            "rtype": resource
        }]}
        return response
