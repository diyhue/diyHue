from configManager import configInit
from datetime import datetime
from time import tzset
import os
import json
import logManager
import yaml
import uuid
import weakref
from HueObjects import Light, Group, Scene, ApiUser, Rule, ResourceLink, Schedule, Sensor, BehaviorInstance
logging = logManager.logger.get_logger(__name__)

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

def _open_yaml(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return yaml.load(fp, Loader=yaml.FullLoader)

def _write_yaml(path, contents):
    with open(path, 'w', encoding="utf-8") as fp:
        yaml.dump(contents, fp , Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False )


class Config:
    yaml_config = None
    projectDir = '/opt/hue-emulator'
    configDir = projectDir + '/config'

    def __init__(self):
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)

    def load_config(self):
        self.yaml_config = {"apiUsers": {}, "lights": {}, "groups": {}, "scenes": {}, "config": {}, "rules": {}, "resourcelinks": {}, "schedules": {}, "sensors": {}, "behavior_instance": {}, "temp": {"eventstream": [], "scanResult": {"lastscan": "none"}, "detectedLights": [], "gradientStripLights": {}}}
        try:
            #load config
            if os.path.exists(self.configDir + "/config.yaml"):
                config = _open_yaml(self.configDir + "/config.yaml")
                os.environ['TZ'] = config["timezone"]
                tzset()
                config["apiUsers"] = {}
                for user, data in config["whitelist"].items():
                    self.yaml_config["apiUsers"][user] = ApiUser(user, data["name"], data["client_key"], data["create_date"], data["last_use_date"])
                del config["whitelist"]
                self.yaml_config["config"] = config
            else:
                self.yaml_config["config"] = {"Remote API enabled": False, "Hue Essentials key": str(uuid.uuid1()).replace('-', ''), "mqtt":{"enabled":False},"deconz":{"enabled":False},"alarm":{"on":False, "lasttriggered": 0},"apiUsers":{},"apiversion":"1.44.0","name":"DiyHue Bridge","netmask":"255.255.255.0","swversion":"1945091050","timezone":"Europe/London","linkbutton":{"lastlinkbuttonpushed": 1599398980},"users":{"admin@diyhue.org":{"password":"pbkdf2:sha256:150000$bqqXSOkI$199acdaf81c18f6ff2f29296872356f4eb78827784ce4b3f3b6262589c788742"}}, "hue": {}, "tradfri": {}}
            # load lights
            if os.path.exists(self.configDir + "/lights.yaml"):
                lights = _open_yaml(self.configDir + "/lights.yaml")
                for light, data in lights.items():
                    data["id_v1"] = light
                    self.yaml_config["lights"][light] = Light(data)
                    #self.yaml_config["groups"]["0"].add_light(self.yaml_config["lights"][light])
            #groups
            #create group 0
            self.yaml_config["groups"]["0"] = Group({"name":"Group 0","id_v1": "0","type":"LightGroup","state":{"all_on":False,"any_on":True},"recycle":False,"action":{"on":False,"bri":165,"hue":8418,"sat":140,"effect":"none","xy":[0.6635,0.2825],"ct":366,"alert":"select","colormode":"hs"}})
            for key, light in self.yaml_config["lights"].items():
                self.yaml_config["groups"]["0"].add_light(light)
            # create groups
            if os.path.exists(self.configDir + "/groups.yaml"):
                groups = _open_yaml(self.configDir + "/groups.yaml")
                for group, data in groups.items():
                    data["id_v1"] = group
                    self.yaml_config["groups"][group] = Group(data)
                    #   Reference lights objects instead of id's
                    for light in data["lights"]:
                        self.yaml_config["groups"][group].add_light(self.yaml_config["lights"][light])
                    if "locations" in data:
                        for light, location in data["locations"].items():
                            lightObj = self.yaml_config["lights"][light]
                            self.yaml_config["groups"][group].locations[lightObj] = location
            #scenes
            if os.path.exists(self.configDir + "/scenes.yaml"):
                scenes = _open_yaml(self.configDir + "/scenes.yaml")
                for scene, data in scenes.items():
                    data["id_v1"] = scene
                    if data["type"] == "GroupScene":
                        group = weakref.ref(self.yaml_config["groups"][data["group"]])
                        data["lights"] = group().lights
                        data["group"] = group
                    else:
                        objctsList = []
                        for light in data["lights"]:
                            objctsList.append(weakref.ref(self.yaml_config["lights"][light]))
                        data["lights"] = objctsList
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["scenes"][scene] = Scene(data)
                    for light, lightstate in data["lightstates"].items():
                        lightObj = self.yaml_config["lights"][light]
                        self.yaml_config["scenes"][scene].lightstates[lightObj] = lightstate

            #rules
            if os.path.exists(self.configDir + "/rules.yaml"):
                rules = _open_yaml(self.configDir + "/rules.yaml")
                for rule, data in rules.items():
                    data["id_v1"] = rule
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["rules"][rule] = Rule(data)
            #schedules
            if os.path.exists(self.configDir + "/schedules.yaml"):
                schedules = _open_yaml(self.configDir + "/schedules.yaml")
                for schedule, data in schedules.items():
                    data["id_v1"] = schedule
                    self.yaml_config["schedules"][schedule] = Schedule(data)
            #sensors
            if os.path.exists(self.configDir + "/sensors.yaml"):
                sensors = _open_yaml(self.configDir + "/sensors.yaml")
                for sensor, data in sensors.items():
                    data["id_v1"] = sensor
                    self.yaml_config["sensors"][sensor] = Sensor(data)
                    self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"][sensor])
            else:
                data = {"modelid": "PHDL00", "name": "Daylight", "type": "Daylight", "id_v1": "1"}
                self.yaml_config["sensors"]["1"] = Sensor(data)
                self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"]["1"])
            #resourcelinks
            if os.path.exists(self.configDir + "/resourcelinks.yaml"):
                resourcelinks = _open_yaml(self.configDir + "/resourcelinks.yaml")
                for resourcelink, data in resourcelinks.items():
                    data["id_v1"] = resourcelink
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["resourcelinks"][resourcelink] = ResourceLink(data)
            #behavior_instance
            if os.path.exists(self.configDir + "/behavior_instance.yaml"):
                behavior_instance = _open_yaml(self.configDir + "/behavior_instance.yaml")
                for behavior_instance, data in behavior_instance.items():
                    self.yaml_config["behavior_instance"][behavior_instance] = BehaviorInstance(data)

            logging.info("Config loaded")
        except Exception:
            logging.exception("CRITICAL! Config file was not loaded")
            raise SystemExit("CRITICAL! Config file was not loaded")
        bridgeConfig = self.yaml_config


    def save_config(self, backup=False, resource="all"):
        path = self.configDir + '/'
        if backup:
            path = self.configDir + '/backup/'
            if not os.path.exists(path):
                os.makedirs(path)
        config = self.yaml_config["config"]
        config["whitelist"] = {}
        for user, obj in self.yaml_config["apiUsers"].items():
            config["whitelist"][user] = obj.save()

        if resource in ["all", "config"]:
            _write_yaml(path + "config.yaml", config)
            logging.debug("Dump config file " + path + "config.yaml")
        saveResources = []
        if resource == "all":
            saveResources = ["lights", "groups", "scenes", "rules", "resourcelinks", "schedules", "sensors", "behavior_instance"]
        else:
            saveResources.append(resource)
        for object in saveResources:
            filePath = path + object + ".yaml"
            dumpDict = {}
            for element in self.yaml_config[object]:
                if element != "0":
                    dumpDict[self.yaml_config[object][element].id_v1] = self.yaml_config[object][element].save()
            _write_yaml(filePath, dumpDict)
            logging.debug("Dump config file " + filePath)


    def reset_config(self):
        backup = self.save_config(True)
        try:
            os.remove(self.configDir + "/*.yaml")
        except:
            logging.exception("Something went wrong when deleting the config")
        self.load_config()
        return backup

    def write_args(self, args):
        self.yaml_config = configInit.write_args(args, self.yaml_config)

    def generate_security_key(self):
        self.yaml_config = configInit.generate_security_key(self.yaml_config)
