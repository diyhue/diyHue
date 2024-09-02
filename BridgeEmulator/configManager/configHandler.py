from configManager import configInit
from configManager.argumentHandler import parse_arguments
import os
import pathlib
import subprocess
import logManager
import yaml
import uuid
import weakref
from HueObjects import Light, Group, EntertainmentConfiguration, Scene, ApiUser, Rule, ResourceLink, Schedule, Sensor, BehaviorInstance, SmartScene
try:
    from time import tzset
except ImportError:
    tzset = None

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
    configDir = parse_arguments()["CONFIG_PATH"]
    runningDir = str(pathlib.Path(__file__)).replace("/configManager/configHandler.py","")

    def __init__(self):
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)

    def load_config(self):
        self.yaml_config = {"apiUsers": {}, "lights": {}, "groups": {}, "scenes": {}, "config": {}, "rules": {}, "resourcelinks": {}, "schedules": {}, "sensors": {}, "behavior_instance": {}, "geofence_clients": {}, "smart_scene": {}, "temp": {"eventstream": [], "scanResult": {"lastscan": "none"}, "detectedLights": [], "gradientStripLights": {}}}
        try:
            #load config
            if os.path.exists(self.configDir + "/config.yaml"):
                config = _open_yaml(self.configDir + "/config.yaml")
                os.environ['TZ'] = config["timezone"]
                if tzset is not None:
                    tzset()
                config["apiUsers"] = {}
                for user, data in config["whitelist"].items():
                    self.yaml_config["apiUsers"][user] = ApiUser.ApiUser(user, data["name"], data["client_key"], data["create_date"], data["last_use_date"])
                del config["whitelist"]
                # updgrade config
                if "homeassistant" not in config:
                    config["homeassistant"] = {"enabled": False}
                if "yeelight" not in config:
                    config["yeelight"] = {"enabled": True}
                if "native_multi" not in config:
                    config["native_multi"] = {"enabled": True}
                if "tasmota" not in config:
                    config["tasmota"] = {"enabled": True}
                if "wled" not in config:
                    config["wled"] = {"enabled": True}
                if "shelly" not in config:
                    config["shelly"] = {"enabled": True}
                if "esphome" not in config:
                    config["esphome"] = {"enabled": True}
                if "hyperion" not in config:
                    config["hyperion"] = {"enabled": True}
                if "tpkasa" not in config:
                    config["tpkasa"] = {"enabled": True}
                if "elgato" not in config:
                    config["elgato"] = {"enabled": True}
                if "port" not in config:
                    config["port"] = {"enabled": False,"ports": [80]}
                if "zigbee_device_discovery_info" not in config:
                    config["zigbee_device_discovery_info"] = {"status": "ready"}
                if "swupdate2" not in config:
                    config["swupdate2"] = {"autoinstall": {
                                                "on": False,
                                                "updatetime": "T14:00:00"
                                            },
                                            "bridge": {
                                                "lastinstall": "2020-12-11T17:08:55",
                                                "state": "noupdates"
                                            },
                                            "checkforupdate": False,
                                            "lastchange": "2020-12-13T10:30:15",
                                            "state": "noupdates",
                                            "install": False
                                            }

                if int(config["swversion"]) < 1958077010:
                    config["swversion"] = "1965111030"
                if float(config["apiversion"][:3]) < 1.56:
                    config["apiversion"] = "1.65.0"

                self.yaml_config["config"] = config
            else:
                self.yaml_config["config"] = {
                    "Remote API enabled": False,
                    "Hue Essentials key": str(uuid.uuid1()).replace('-', ''),
                    "discovery": True,
                    "mqtt":{"enabled":False},
                    "deconz":{"enabled":False},
                    "alarm":{"enabled": False,"lasttriggered": 0},
                    "port":{"enabled": False,"ports": [80]},
                    "apiUsers":{},
                    "apiversion":"1.65.0",
                    "name":"DiyHue Bridge",
                    "netmask":"255.255.255.0",
                    "swversion":"1965111030",
                    "timezone":parse_arguments()["TZ"],
                    "linkbutton":{"lastlinkbuttonpushed": 1599398980},
                    "users":{"admin@diyhue.org":{"password":"pbkdf2:sha256:150000$bqqXSOkI$199acdaf81c18f6ff2f29296872356f4eb78827784ce4b3f3b6262589c788742"}},
                    "hue": {},
                    "tradfri": {},
                    "homeassistant": {"enabled":False},
                    "yeelight": {"enabled":True},
                    "native_multi": {"enabled":True},
                    "tasmota": {"enabled":True},
                    "wled": {"enabled":True},
                    "shelly": {"enabled":True},
                    "esphome": {"enabled":True},
                    "hyperion": {"enabled":True},
                    "tpkasa": {"enabled":True},
                    "elgato": {"enabled":True},
                    "zigbee_device_discovery_info": {"status": "ready"},
                    "swupdate2": {  "autoinstall": {
                                        "on": False,
                                        "updatetime": "T14:00:00"
                                    },
                                    "bridge": {
                                        "lastinstall": "2020-12-11T17:08:55",
                                        "state": "noupdates"
                                    },
                                    "checkforupdate": False,
                                    "lastchange": "2020-12-13T10:30:15",
                                    "state": "noupdates",
                                    "install": False
                                    }
                }
            # load lights
            if os.path.exists(self.configDir + "/lights.yaml"):
                lights = _open_yaml(self.configDir + "/lights.yaml")
                for light, data in lights.items():
                    data["id_v1"] = light
                    self.yaml_config["lights"][light] = Light.Light(data)
                    #self.yaml_config["groups"]["0"].add_light(self.yaml_config["lights"][light])
            #groups
            #create group 0
            self.yaml_config["groups"]["0"] = Group.Group({"name":"Group 0","id_v1": "0","type":"LightGroup","state":{"all_on":False,"any_on":True},"recycle":False,"action":{"on":False,"bri":165,"hue":8418,"sat":140,"effect":"none","xy":[0.6635,0.2825],"ct":366,"alert":"select","colormode":"hs"}})
            for key, light in self.yaml_config["lights"].items():
                self.yaml_config["groups"]["0"].add_light(light)
            # create groups
            if os.path.exists(self.configDir + "/groups.yaml"):
                groups = _open_yaml(self.configDir + "/groups.yaml")
                for group, data in groups.items():
                    data["id_v1"] = group
                    if data["type"] == "Entertainment":
                        self.yaml_config["groups"][group] = EntertainmentConfiguration.EntertainmentConfiguration(data)
                        for light in data["lights"]:
                            self.yaml_config["groups"][group].add_light(self.yaml_config["lights"][light])
                        if "locations" in data:
                            for light, location in data["locations"].items():
                                lightObj = self.yaml_config["lights"][light]
                                self.yaml_config["groups"][group].locations[lightObj] = location
                    else:
                        if "owner" in data and isinstance(data["owner"], dict):
                            data["owner"] = self.yaml_config["apiUsers"][list(self.yaml_config["apiUsers"])[0]]
                        elif "owner" not in data:
                            data["owner"] = self.yaml_config["apiUsers"][list(self.yaml_config["apiUsers"])[0]]
                        else:
                            data["owner"] = self.yaml_config["apiUsers"][data["owner"]]
                        self.yaml_config["groups"][group] = Group.Group(data)
                        for light in data["lights"]:
                            self.yaml_config["groups"][group].add_light(self.yaml_config["lights"][light])

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
                    self.yaml_config["scenes"][scene] = Scene.Scene(data)
                    for light, lightstate in data["lightstates"].items():
                        lightObj = self.yaml_config["lights"][light]
                        self.yaml_config["scenes"][scene].lightstates[lightObj] = lightstate
            #smart_scene
            if os.path.exists(self.configDir + "/smart_scene.yaml"):
                smart_scene = _open_yaml(self.configDir + "/smart_scene.yaml")
                for scene, data in smart_scene.items():
                    data["id_v1"] = scene
                    self.yaml_config["smart_scene"][scene] = SmartScene.SmartScene(data)
            #rules
            if os.path.exists(self.configDir + "/rules.yaml"):
                rules = _open_yaml(self.configDir + "/rules.yaml")
                for rule, data in rules.items():
                    data["id_v1"] = rule
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["rules"][rule] = Rule.Rule(data)
            #schedules
            if os.path.exists(self.configDir + "/schedules.yaml"):
                schedules = _open_yaml(self.configDir + "/schedules.yaml")
                for schedule, data in schedules.items():
                    data["id_v1"] = schedule
                    self.yaml_config["schedules"][schedule] = Schedule.Schedule(data)
            #sensors
            if os.path.exists(self.configDir + "/sensors.yaml"):
                sensors = _open_yaml(self.configDir + "/sensors.yaml")
                for sensor, data in sensors.items():
                    data["id_v1"] = sensor
                    self.yaml_config["sensors"][sensor] = Sensor.Sensor(data)
                    self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"][sensor])
            else:
                data = {"modelid": "PHDL00", "name": "Daylight", "type": "Daylight", "id_v1": "1"}
                self.yaml_config["sensors"]["1"] = Sensor.Sensor(data)
                self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"]["1"])
            #resourcelinks
            if os.path.exists(self.configDir + "/resourcelinks.yaml"):
                resourcelinks = _open_yaml(self.configDir + "/resourcelinks.yaml")
                for resourcelink, data in resourcelinks.items():
                    data["id_v1"] = resourcelink
                    owner = self.yaml_config["apiUsers"][data["owner"]]
                    data["owner"] = owner
                    self.yaml_config["resourcelinks"][resourcelink] = ResourceLink.ResourceLink(data)
            #behavior_instance
            if os.path.exists(self.configDir + "/behavior_instance.yaml"):
                behavior_instance = _open_yaml(self.configDir + "/behavior_instance.yaml")
                for behavior_instance, data in behavior_instance.items():
                    self.yaml_config["behavior_instance"][behavior_instance] = BehaviorInstance.BehaviorInstance(data)

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
        if resource in ["all", "config"]:
            config = self.yaml_config["config"]
            config["whitelist"] = {}
            for user, obj in self.yaml_config["apiUsers"].items():
                config["whitelist"][user] = obj.save()
            _write_yaml(path + "config.yaml", config)
            logging.debug("Dump config file " + path + "config.yaml")
            if resource == "config":
                return
        saveResources = []
        if resource == "all":
            saveResources = ["lights", "groups", "scenes", "rules", "resourcelinks", "schedules", "sensors", "behavior_instance", "smart_scene"]
        else:
            saveResources.append(resource)
        for object in saveResources:
            filePath = path + object + ".yaml"
            dumpDict = {}
            for element in self.yaml_config[object]:
                if element != "0":
                    savedData = self.yaml_config[object][element].save()
                    if savedData:
                        dumpDict[self.yaml_config[object][element].id_v1] = savedData
            _write_yaml(filePath, dumpDict)
            logging.debug("Dump config file " + filePath)

    def reset_config(self):
        backup = self.save_config(backup=True)
        try:
            os.popen('rm -r ' + self.configDir + '/*.yaml')
        except:
            logging.exception("Something went wrong when deleting the config")
        self.load_config()
        return backup

    def restore_backup(self):
        try:
            os.popen('rm -r ' + self.configDir + '/*.yaml')
        except:
            logging.exception("Something went wrong when deleting the config")
        subprocess.run('cp -r ' + self.configDir + '/backup/*.yaml ' + self.configDir + '/', shell=True, capture_output=True, text=True)
        load = self.load_config()
        return load

    def download_config(self):
        self.save_config()
        subprocess.run('tar --exclude=' + "'config_debug.yaml'" + ' -cvf ' + self.configDir + '/config.tar ' + self.configDir + '/*.yaml', shell=True, capture_output=True, text=True)
        return self.configDir + "/config.tar"

    def download_log(self):
        subprocess.run('tar -cvf ' + self.configDir + '/diyhue_log.tar ' +
                 self.runningDir + '/*.log* ',
                 shell=True, capture_output=True, text=True)
        return self.configDir + "/diyhue_log.tar"

    def download_debug(self):
        _write_yaml(self.configDir + "/config_debug.yaml", self.yaml_config["config"])
        debug = _open_yaml(self.configDir + "/config_debug.yaml")
        debug["whitelist"] = "privately"
        debug["Hue Essentials key"] = "privately"
        debug["users"] = "privately"
        info = {}
        info["OS"] = os.uname().sysname
        info["Architecture"] = os.uname().machine
        info["os_version"] = os.uname().version
        info["os_release"] = os.uname().release
        info["Hue-Emulator Version"] = subprocess.run("stat -c %y HueEmulator3.py", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        info["WebUI Version"] = subprocess.run("stat -c %y flaskUI/templates/index.html", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        _write_yaml(self.configDir + "/config_debug.yaml", debug)
        _write_yaml(self.configDir + "/system_info.yaml", info)
        subprocess.run('tar --exclude=' + "'config.yaml'" + ' -cvf ' + self.configDir + '/config_debug.tar ' +
                 self.configDir + '/*.yaml ' +
                 self.runningDir + '/*.log* ',
                 shell=True, capture_output=True, text=True)
        os.popen('rm -r ' + self.configDir + '/config_debug.yaml')
        return self.configDir + "/config_debug.tar"

    def write_args(self, args):
        self.yaml_config = configInit.write_args(args, self.yaml_config)

    def generate_security_key(self):
        self.yaml_config = configInit.generate_security_key(self.yaml_config)
