import uuid
from random import randrange


def _generate_unique_id():
    rand_bytes = [randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])


def write_args(args, json_config):
    host_ip = args["HOST_IP"]
    ip_pieces = host_ip.split(".")
    json_config["config"]["ipaddress"] = host_ip
    json_config["config"]["gateway"] = ip_pieces[0] + "." + ip_pieces[1] + "." + ip_pieces[2] + ".1"
    json_config["config"]["mac"] = args["FULLMAC"]
    json_config["config"]["bridgeid"] = (args["MAC"][:6] + 'FFFE' + args["MAC"][6:]).upper()
    return json_config


def generate_security_key(json_config):
    # generate security key for Hue Essentials remote access
    if not json_config["config"].get("Hue Essentials key"):
        json_config["config"]["Hue Essentials key"] = str(uuid.uuid1()).replace('-', '')
    return json_config


def sanitizeBridgeScenes(json_config):
    for scene in list(json_config["scenes"]):
        if "type" in json_config["scenes"][scene] and json_config["scenes"][scene][
            "type"] == "GroupScene":  # scene has "type" key and "type" is "GroupScene"
            if json_config["scenes"][scene]["group"] not in json_config["groups"]:  # the group don't exist
                del json_config["scenes"][scene]  # delete the group
                continue  # avoid KeyError on next if statement
            else:
                for lightstate in list(json_config["scenes"][scene]["lightstates"]):
                    if lightstate not in json_config["groups"][json_config["scenes"][scene]["group"]][
                        "lights"]:  # if the light is no longer member in the group:
                        del json_config["scenes"][scene]["lightstates"][
                            lightstate]  # delete the lighstate of the missing light
        else:  # must be a lightscene
            for lightstate in list(json_config["scenes"][scene]["lightstates"]):
                if lightstate not in json_config["lights"]:  # light is not present anymore on the bridge
                    del (json_config["scenes"][scene]["lightstates"][lightstate])  # delete invalid lightstate

        if "lightstates" in json_config["scenes"][scene] and len(
                json_config["scenes"][scene]["lightstates"]) == 0:  # empty scenes are useless
            del json_config["scenes"][scene]
    return json_config


def updateConfig(json_config):

    #### bridge emulator config

    if int(json_config["config"]["swversion"]) < 1939070020:
        json_config["config"]["swversion"] = "1939070020"
        json_config["config"]["apiversion"] = "1.35.0"

    ### end bridge config

    if "emulator" not in json_config:
        json_config["emulator"] = {"lights": {}, "sensors": {}}


    if "alarm" not in json_config["emulator"]:
        json_config["emulator"]["alarm"] = {"on": False, "email": "", "lasttriggered": 100000}
    if "alarm_config" in json_config:
        del json_config["alarm_config"]

    if "mqtt" not in json_config["emulator"]:
        json_config["emulator"]["mqtt"] = { "discoveryPrefix": "homeassistant", "enabled": False, "mqttPassword": "", "mqttPort": 1883, "mqttServer": "mqtt", "mqttUser": ""}

    if "Remote API enabled" not in json_config["config"]:
        json_config["config"]["Remote API enabled"] = False

    # Update deCONZ sensors
    for sensor_id, sensor in json_config["deconz"]["sensors"].items():
        if "modelid" not in sensor:
            sensor["modelid"] = json_config["sensors"][sensor["bridgeid"]]["modelid"]
        if sensor["modelid"] == "TRADFRI motion sensor":
            if "lightsensor" not in sensor:
                sensor["lightsensor"] = "internal"

    # Update scenes
    for scene_id, scene in json_config["scenes"].items():
        if "type" not in scene:
            scene["type"] = "LightGroup"

    # Update sensors
    for sensor_id, sensor in json_config["sensors"].items():
        if sensor["type"] == "CLIPGenericStatus":
            sensor["state"]["status"] = 0
        elif sensor["type"] == "ZLLTemperature" and sensor["modelid"] == "SML001" and sensor["manufacturername"] == "Philips":
            sensor["capabilities"] = {"certified": True, "primary": False}
            sensor["swupdate"] = {"lastinstall": "2019-03-16T21:16:21","state": "noupdates"}
            sensor["swversion"] = "6.1.1.27575"
        elif sensor["type"] == "ZLLPresence" and sensor["modelid"] == "SML001" and sensor["manufacturername"] == "Philips":
            sensor["capabilities"] = {"certified": True, "primary": True}
            sensor["swupdate"] = {"lastinstall": "2019-03-16T21:16:21","state": "noupdates"}
            sensor["swversion"] = "6.1.1.27575"
        elif sensor["type"] == "ZLLLightLevel" and sensor["modelid"] == "SML001" and sensor["manufacturername"] == "Philips":
            sensor["capabilities"] = {"certified": True, "primary": False}
            sensor["swupdate"] = {"lastinstall": "2019-03-16T21:16:21","state": "noupdates"}
            sensor["swversion"] = "6.1.1.27575"

    # Update lights
    for light_id, light_address in json_config["lights_address"].items():
        light = json_config["lights"][light_id]

        if light_address["protocol"] == "native" and "mac" not in light_address:
            light_address["mac"] = light["uniqueid"][:17]
            light["uniqueid"] = _generate_unique_id()

        # Update deCONZ protocol lights
        if light_address["protocol"] == "deconz":
            # Delete old keys
            for key in list(light):
                if key in ["hascolor", "ctmax", "ctmin", "etag"]:
                    del light[key]

            if light["modelid"].startswith("TRADFRI"):
                light.update({"manufacturername": "Philips", "swversion": "1.46.13_r26312"})

                light["uniqueid"] = _generate_unique_id()

                if light["type"] == "Color temperature light":
                    light["modelid"] = "LTW001"
                elif light["type"] == "Color light":
                    light["modelid"] = "LCT015"
                    light["type"] = "Extended color light"
                elif light["type"] == "Dimmable light":
                    light["modelid"] = "LWB010"

        # Update Philips lights firmware version
        if "manufacturername" in light and light["manufacturername"] == "Philips":
            swversion = "1.46.13_r26312"
            if light["modelid"] in ["LST002", "LCT015", "LTW001", "LWB010"]:
                # Update archetype for various Philips models
                if light["modelid"] in ["LTW001", "LWB010"]:
                    archetype = "classicbulb"
                    light["productname"] = "Hue white lamp"
                    light["productid"] = "Philips-LWB014-1-A19DLv3"
                    light["capabilities"] = {"certified": True,"control": {"ct": {"max": 500,"min": 153},"maxlumen": 840,"mindimlevel": 5000},"streaming": {"proxy": False,"renderer": False}}
                elif light["modelid"] == "LCT015":
                    archetype = "sultanbulb"
                    light["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]],"colorgamuttype": "C","ct": {"max": 500,"min": 153},"maxlumen": 800,"mindimlevel": 1000},"streaming": {"proxy": True,"renderer": True}}
                    light["productname"] = "Hue color lamp"
                elif light["modelid"] == "LST002":
                    archetype = "huelightstrip"
                    swversion = "5.127.1.26581"
                    light["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.704,0.296],[0.2151,0.7106],[0.138,0.08]],"colorgamuttype": "A","maxlumen": 200,"mindimlevel": 10000},"streaming": {"proxy": False,"renderer": True}}
                    light["productname"] = "Hue lightstrip plus"

                light["config"] = {"archetype": archetype, "function": "mixed", "direction": "omnidirectional"}

                if "mode" in light["state"]:
                    light["state"]["mode"] = "homeautomation"

                # Update startup config
                if "startup" not in light["config"]:
                    light["config"]["startup"] = {"mode": "safety", "configured": False}

            # Finally, update the software version
            light["swversion"] = swversion

    #set entertainment streaming to inactive on start/restart
    for group_id, group in json_config["groups"].items():
        if "type" in group and group["type"] == "Entertainment":
            if "stream" not in group:
                group["stream"] = {}
            group["stream"].update({"active": False, "owner": None})

        group["sensors"] = []

    #fix timezones bug
    if "values" not in json_config["capabilities"]["timezones"]:
        timezones = json_config["capabilities"]["timezones"]
        json_config["capabilities"]["timezones"] = {"values": timezones}
    return json_config
