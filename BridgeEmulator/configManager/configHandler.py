from configManager import configInit
from configManager.argumentHandler import parse_arguments, generate_certificate
import os
import pathlib
import subprocess
import logManager
import yaml
import uuid
import weakref
import threading
import time
import glob
import shutil
from copy import deepcopy
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

def _safe_open_yaml(path, default=None):
    """Open a YAML file safely. Returns default on any error.
    Corrupt files are renamed to <path>.corrupt for manual recovery."""
    if not os.path.exists(path):
        return default if default is not None else {}

    try:
        with open(path, 'r', encoding="utf-8") as fp:
            data = yaml.load(fp, Loader=yaml.FullLoader)
    except Exception as e:
        logging.error(f"Failed to parse {path}: {e}")
        corrupt_path = path + ".corrupt"
        try:
            os.rename(path, corrupt_path)
            logging.warning(f"Renamed corrupt config to {corrupt_path} — starting with defaults")
        except OSError as e2:
            logging.error(f"Could not rename corrupt file {path}: {e2}")
        return default if default is not None else {}

    if data is None:
        return default if default is not None else {}
    if not isinstance(data, dict):
        logging.error(f"{path} is not a dict (got {type(data).__name__}), renaming")
        corrupt_path = path + ".corrupt"
        try:
            os.rename(path, corrupt_path)
        except OSError:
            pass
        return default if default is not None else {}
    return data

def _write_yaml(path, contents):
    tmp_path = path + ".tmp"
    with open(tmp_path, 'w', encoding="utf-8") as fp:
        yaml.dump(contents, fp, Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False)
    os.replace(tmp_path, path)  # atomic on same filesystem (POSIX)

class Config:
    # Single source of truth for all config file I/O — both reads and writes.
    # Maps resource key → backing YAML filename.
    # Used by: load_config(), save_config(), mark_dirty(), and V2 API handlers.
    CONFIG_FILES = {
        "config":            "config.yaml",
        "lights":            "lights.yaml",
        "groups":            "groups.yaml",
        "scenes":            "scenes.yaml",
        "rules":             "rules.yaml",
        "resourcelinks":     "resourcelinks.yaml",
        "schedules":         "schedules.yaml",
        "sensors":           "sensors.yaml",
        "behavior_instance": "behavior_instance.yaml",
        "smart_scene":       "smart_scene.yaml",
    }

    # Maps V2 API resource types → V1 resource keys (used by DELETE handler).
    # Values must be keys in CONFIG_FILES, or None for memory-only resources.
    V2_TO_V1_RESOURCE = {
        "room": "groups", "zone": "groups",
        "entertainment_configuration": "groups", "entertainment": "groups",
        "grouped_light": "groups",
        "scene": "scenes", "smart_scene": "smart_scene",
        "behavior_instance": "behavior_instance",
        "light": "lights", "device": "config",
        "sensor": "sensors", "motion": "sensors",
        "light_level": "sensors", "temperature": "sensors",
        "button": "sensors", "relative_rotary": "sensors",
        "geofence_client": None,  # memory-only, no backing file
    }

    yaml_config = None
    argsDict = parse_arguments()
    configDir = argsDict["CONFIG_PATH"]
    runningDir = str(pathlib.Path(__file__)).replace("/configManager/configHandler.py","")

    def _config_path(self, resource, subdir=None):
        """Return the full filesystem path for a config resource.
        Args:
            resource: key in CONFIG_FILES (e.g. 'groups')
            subdir: optional subdirectory under configDir (e.g. 'backup')
        """
        if subdir:
            return os.path.join(self.configDir, subdir, self.CONFIG_FILES[resource])
        return os.path.join(self.configDir, self.CONFIG_FILES[resource])

    def __init__(self):
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)
        self._dirty_resources = set()
        self._last_dirty_time = 0.0
        self._save_lock = threading.RLock()
        self._save_debounce_s = 5.0

    def mark_dirty(self, resource):
        """Mark a resource as needing persistence. Safe to call from any thread."""
        if resource not in self.CONFIG_FILES:
            return
        with self._save_lock:
            is_new = resource not in self._dirty_resources
            self._dirty_resources.add(resource)
            self._last_dirty_time = time.time()
        if is_new:
            logging.debug(f"Config marked dirty: {resource}")

    def save_dirty_if_needed(self):
        """Called by scheduler each tick. Saves if dirty AND debounce elapsed.
        Uses non-blocking lock — skips if a save is already in progress."""
        if not self._dirty_resources:
            return
        acquired = self._save_lock.acquire(blocking=False)
        if not acquired:
            return  # save already in progress, next tick will catch stragglers
        try:
            elapsed = time.time() - self._last_dirty_time
            if elapsed < self._save_debounce_s:
                return
            # Snapshot and clear dirty set under lock
            to_save = list(self._dirty_resources)
            self._dirty_resources.clear()
        finally:
            self._save_lock.release()
        # Save outside the lock to avoid holding it during disk I/O
        logging.info(f"Persisting dirty resources: {to_save}")
        for resource in to_save:
            try:
                self.save_config(backup=False, resource=resource)
                logging.debug(f"Saved dirty resource: {resource}")
            except Exception as e:
                logging.error(f"Failed to save {resource}: {e}")
                # Re-mark dirty so next tick retries
                with self._save_lock:
                    self._dirty_resources.add(resource)

    def load_config(self):
        if self.yaml_config is None:
            self.yaml_config = {"apiUsers": {}, "lights": {}, "groups": {}, "scenes": {}, "config": {}, "rules": {}, "resourcelinks": {}, "schedules": {}, "sensors": {}, "behavior_instance": {}, "geofence_clients": {}, "smart_scene": {}, "temp": {"eventstream": [], "scanResult": {"lastscan": "none"}, "detectedLights": [], "gradientStripLights": {}}}
        else:
            # Mutate in-place so captured module-global references stay valid
            # (restful.py:26, v2restapi.py:20, scheduler.py:15, etc.)
            self.yaml_config.clear()
            self.yaml_config.update({
                "apiUsers": {}, "lights": {}, "groups": {}, "scenes": {},
                "config": {}, "rules": {}, "resourcelinks": {}, "schedules": {},
                "sensors": {}, "behavior_instance": {}, "geofence_clients": {},
                "smart_scene": {}, "temp": {"eventstream": [], "scanResult": {"lastscan": "none"}, "detectedLights": [], "gradientStripLights": {}}
            })

        # load config
        if os.path.exists(self._config_path("config")):
            config = _safe_open_yaml(self._config_path("config"))
            if config is None:
                config = {}
            if not config:
                logging.critical("config.yaml loaded empty — starting with minimal defaults")
                config = {"timezone": "Europe/London"}
            if "timezone" not in config:
                logging.warn("No Time Zone in config, please set Time Zone in webui, default to Europe/London")
                config["timezone"] = "Europe/London"
            os.environ['TZ'] = config["timezone"]
            if tzset is not None:
                tzset()
            config["apiUsers"] = {}
            if "whitelist" in config:
                for user, data in config["whitelist"].items():
                    try:
                        self.yaml_config["apiUsers"][user] = ApiUser.ApiUser(user, data["name"], data["client_key"], data["create_date"], data["last_use_date"])
                    except Exception as e:
                        logging.error(f"Skipping corrupt apiUser {user}: {e}")
                del config["whitelist"]
            # upgrade config
            if "discovery" not in config:
                config["discovery"] = True
            if "IP_RANGE" not in config:
                config["IP_RANGE"] = {
                    "IP_RANGE_START": 0,
                    "IP_RANGE_END": 255,
                    "SUB_IP_RANGE_START": int(self.argsDict["HOST_IP"].split('.')[2]),
                    "SUB_IP_RANGE_END": int(self.argsDict["HOST_IP"].split('.')[2])}
            if "scanonhostip" not in config:
                config["scanonhostip"] = False
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
            if "govee" not in config:
                config["govee"] = {"enabled": False}
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
                config["swversion"] = "1967054020"
            if float(config["apiversion"][:3]) < 1.56:
                config["apiversion"] = "1.67.0"
            if "linkbutton" not in config or type(config["linkbutton"]) == bool or "lastlinkbuttonpushed" not in config["linkbutton"]:
                config["linkbutton"] = {"lastlinkbuttonpushed": 1599398980}

            self.yaml_config["config"] = config
        else:
            self.yaml_config["config"] = {
                "Remote API enabled": False,
                "Hue Essentials key": str(uuid.uuid1()).replace('-', ''),
                "discovery": True,
                "scanonhostip": False,
                "mqtt":{"enabled":False},
                "deconz":{"enabled":False},
                "alarm":{"enabled": False,"lasttriggered": 0},
                "port":{"enabled": False,"ports": [80]},
                "apiUsers":{},
                "apiversion":"1.67.0",
                "name":"DiyHue Bridge",
                "netmask":"255.255.255.0",
                "swversion":"1967054020",
                "timezone": "Europe/London",
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
                "govee": {"enabled": False},
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
                },
                "IP_RANGE": {
                    "IP_RANGE_START": 0,
                    "IP_RANGE_END": 255,
                    "SUB_IP_RANGE_START": int(self.argsDict["HOST_IP"].split('.')[2]),
                    "SUB_IP_RANGE_END": int(self.argsDict["HOST_IP"].split('.')[2])
                }
            }
        # load lights
        if os.path.exists(self._config_path("lights")):
            lights = _safe_open_yaml(self._config_path("lights"))
            if lights:
                for light, data in lights.items():
                    try:
                        data["id_v1"] = light
                        self.yaml_config["lights"][light] = Light.Light(data)
                    except Exception as e:
                        logging.error(f"Skipping corrupt light {light}: {e}")
        #groups
        #create group 0
        self.yaml_config["groups"]["0"] = Group.Group({"name":"Group 0","id_v1": "0","type":"LightGroup","state":{"all_on":False,"any_on":True},"recycle":False,"action":{"on":False,"bri":165,"hue":8418,"sat":140,"effect":"none","xy":[0.6635,0.2825],"ct":366,"alert":"select","colormode":"hs"}})
        for key, light in self.yaml_config["lights"].items():
            self.yaml_config["groups"]["0"].add_light(light)
        # create groups
        if os.path.exists(self._config_path("groups")):
            groups = _safe_open_yaml(self._config_path("groups"))
            if groups:
                for group, data in groups.items():
                    try:
                        data["id_v1"] = group
                        if data["type"] == "Entertainment":
                            self.yaml_config["groups"][group] = EntertainmentConfiguration.EntertainmentConfiguration(data)
                            for light in data["lights"]:
                                if light in self.yaml_config["lights"]:
                                    self.yaml_config["groups"][group].add_light(self.yaml_config["lights"][light])
                                else:
                                    logging.warning(f"Group {group} references missing light {light} — skipping")
                            if "locations" in data:
                                for light, location in data["locations"].items():
                                    if light in self.yaml_config["lights"]:
                                        lightObj = self.yaml_config["lights"][light]
                                        self.yaml_config["groups"][group].locations[lightObj] = location
                        else:
                            if self.yaml_config["apiUsers"]:
                                if "owner" in data and isinstance(data["owner"], dict):
                                    data["owner"] = self.yaml_config["apiUsers"][list(self.yaml_config["apiUsers"])[0]]
                                elif "owner" not in data:
                                    data["owner"] = self.yaml_config["apiUsers"][list(self.yaml_config["apiUsers"])[0]]
                                else:
                                    if data["owner"] in self.yaml_config["apiUsers"]:
                                        data["owner"] = self.yaml_config["apiUsers"][data["owner"]]
                                    else:
                                        data["owner"] = self.yaml_config["apiUsers"][list(self.yaml_config["apiUsers"])[0]]
                            else:
                                data["owner"] = None
                            self.yaml_config["groups"][group] = Group.Group(data)
                            for light in data["lights"]:
                                if light in self.yaml_config["lights"]:
                                    self.yaml_config["groups"][group].add_light(self.yaml_config["lights"][light])
                                else:
                                    logging.warning(f"Group {group} references missing light {light} — skipping")
                    except Exception as e:
                        logging.error(f"Skipping corrupt group {group}: {e}")

        #scenes
        if os.path.exists(self._config_path("scenes")):
            scenes = _safe_open_yaml(self._config_path("scenes"))
            if scenes:
                for scene, data in scenes.items():
                    try:
                        data["id_v1"] = scene
                        if data["type"] == "GroupScene":
                            if data["group"] in self.yaml_config["groups"]:
                                group = weakref.ref(self.yaml_config["groups"][data["group"]])
                                data["lights"] = group().lights
                                data["group"] = group
                            else:
                                logging.warning(f"Scene {scene} references missing group {data['group']} — skipping")
                                continue
                        else:
                            objctsList = []
                            for light in data["lights"]:
                                if light in self.yaml_config["lights"]:
                                    objctsList.append(weakref.ref(self.yaml_config["lights"][light]))
                                else:
                                    logging.warning(f"Scene {scene} references missing light {light} — skipping")
                            data["lights"] = objctsList
                        if data["owner"] in self.yaml_config["apiUsers"]:
                            owner = self.yaml_config["apiUsers"][data["owner"]]
                            data["owner"] = owner
                        else:
                            logging.warning(f"Scene {scene} references missing owner {data['owner']} — skipping")
                            continue
                        self.yaml_config["scenes"][scene] = Scene.Scene(data)
                        for light, lightstate in data["lightstates"].items():
                            if light in self.yaml_config["lights"]:
                                lightObj = self.yaml_config["lights"][light]
                                self.yaml_config["scenes"][scene].lightstates[lightObj] = lightstate
                    except Exception as e:
                        logging.error(f"Skipping corrupt scene {scene}: {e}")
        #smart_scene
        if os.path.exists(self._config_path("smart_scene")):
            smart_scene = _safe_open_yaml(self._config_path("smart_scene"))
            if smart_scene:
                for scene, data in smart_scene.items():
                    try:
                        data["id_v1"] = scene
                        self.yaml_config["smart_scene"][scene] = SmartScene.SmartScene(data)
                    except Exception as e:
                        logging.error(f"Skipping corrupt smart_scene {scene}: {e}")
        #rules
        if os.path.exists(self._config_path("rules")):
            rules = _safe_open_yaml(self._config_path("rules"))
            if rules:
                for rule, data in rules.items():
                    try:
                        data["id_v1"] = rule
                        if "owner" in data and data["owner"] in self.yaml_config["apiUsers"]:
                            owner = self.yaml_config["apiUsers"][data["owner"]]
                            data["owner"] = owner
                        else:
                            logging.warning(f"Rule {rule} has invalid owner — skipping")
                            continue
                        self.yaml_config["rules"][rule] = Rule.Rule(data)
                    except Exception as e:
                        logging.error(f"Skipping corrupt rule {rule}: {e}")
        #schedules
        if os.path.exists(self._config_path("schedules")):
            schedules = _safe_open_yaml(self._config_path("schedules"))
            if schedules:
                for schedule, data in schedules.items():
                    try:
                        data["id_v1"] = schedule
                        self.yaml_config["schedules"][schedule] = Schedule.Schedule(data)
                    except Exception as e:
                        logging.error(f"Skipping corrupt schedule {schedule}: {e}")
        #sensors
        if os.path.exists(self._config_path("sensors")):
            sensors = _safe_open_yaml(self._config_path("sensors"))
            if sensors:
                for sensor, data in sensors.items():
                    try:
                        data["id_v1"] = sensor
                        self.yaml_config["sensors"][sensor] = Sensor.Sensor(data)
                        self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"][sensor])
                    except Exception as e:
                        logging.error(f"Skipping corrupt sensor {sensor}: {e}")
            # Create default daylight sensor if missing
            if "1" not in self.yaml_config["sensors"]:
                data = {"modelid": "PHDL00", "name": "Daylight", "type": "Daylight", "id_v1": "1"}
                self.yaml_config["sensors"]["1"] = Sensor.Sensor(data)
                self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"]["1"])
        else:
            data = {"modelid": "PHDL00", "name": "Daylight", "type": "Daylight", "id_v1": "1"}
            self.yaml_config["sensors"]["1"] = Sensor.Sensor(data)
            self.yaml_config["groups"]["0"].add_sensor(self.yaml_config["sensors"]["1"])
        #resourcelinks
        if os.path.exists(self._config_path("resourcelinks")):
            resourcelinks = _safe_open_yaml(self._config_path("resourcelinks"))
            if resourcelinks:
                for resourcelink, data in resourcelinks.items():
                    try:
                        data["id_v1"] = resourcelink
                        if "owner" in data and data["owner"] in self.yaml_config["apiUsers"]:
                            owner = self.yaml_config["apiUsers"][data["owner"]]
                            data["owner"] = owner
                        else:
                            logging.warning(f"Resourcelink {resourcelink} has invalid owner — skipping")
                            continue
                        self.yaml_config["resourcelinks"][resourcelink] = ResourceLink.ResourceLink(data)
                    except Exception as e:
                        logging.error(f"Skipping corrupt resourcelink {resourcelink}: {e}")
        #behavior_instance
        if os.path.exists(self._config_path("behavior_instance")):
            behavior_instance = _safe_open_yaml(self._config_path("behavior_instance"))
            if behavior_instance:
                for bid, data in behavior_instance.items():
                    try:
                        self.yaml_config["behavior_instance"][bid] = BehaviorInstance.BehaviorInstance(data)
                    except Exception as e:
                        logging.error(f"Skipping corrupt behavior_instance {bid}: {e}")

        # Populate whitelist in the live config dict for runtime consumers
        # (devicesRules.py, restful.py read config["whitelist"] directly)
        self.yaml_config["config"]["whitelist"] = {}
        for user, obj in self.yaml_config["apiUsers"].items():
            self.yaml_config["config"]["whitelist"][user] = obj.save()

        logging.info("Config loaded")

    def save_config(self, backup=False, resource="all", blocking=False):
        """Persist config to disk. Acquires _save_lock to serialize against
        restore_backup/reset_config. When blocking=False (scheduler path),
        skips if a restore/reset is in progress; next tick retries.
        Shutdown uses blocking=True."""
        if not self._save_lock.acquire(blocking=blocking):
            return  # restore/reset in progress, skip this save
        try:
            self._save_config_locked(backup, resource)
        finally:
            self._save_lock.release()

    def _save_config_locked(self, backup, resource):
        subdir = 'backup' if backup else None
        if backup and not os.path.exists(os.path.join(self.configDir, 'backup')):
            os.makedirs(os.path.join(self.configDir, 'backup'))

        if resource in ["all", "config"]:
            # Build a write-copy so we never mutate the live config dict
            config_write = deepcopy(self.yaml_config["config"])
            config_write["whitelist"] = {}
            for user, obj in self.yaml_config["apiUsers"].items():
                config_write["whitelist"][user] = obj.save()
            config_path = self._config_path("config", subdir)
            _write_yaml(config_path, config_write)
            logging.debug("Dump config file " + config_path)
            if resource == "config":
                return
        saveResources = []
        if resource == "all":
            saveResources = [r for r in self.CONFIG_FILES if r != "config"]
        else:
            saveResources.append(resource)
        for object in saveResources:
            filePath = self._config_path(object, subdir)
            dumpDict = {}
            for element in self.yaml_config[object]:
                if element != "0":
                    savedData = self.yaml_config[object][element].save()
                    if savedData:
                        dumpDict[self.yaml_config[object][element].id_v1] = savedData

            # Guard: if the in-memory state is empty, check whether a corrupt
            # version was renamed on load. If so, refuse to overwrite — the
            # user needs to fix the .corrupt file and restart. If no .corrupt
            # file exists, the empty state is legitimate (user deleted all objects).
            if not dumpDict:
                corrupt_path = filePath + ".corrupt"
                if os.path.exists(corrupt_path):
                    logging.warning(
                        f"Refusing to overwrite {filePath} with empty data — "
                        f"corrupt backup exists at {corrupt_path}. Fix it and restart."
                    )
                    continue

            _write_yaml(filePath, dumpDict)
            logging.debug("Dump config file " + filePath)

    def reset_config(self):
        # Save current state to backup before destroying (blocking — must succeed)
        self.save_config(backup=True, blocking=True)

        with self._save_lock:
            for yf in glob.glob(os.path.join(self.configDir, '*.yaml')):
                try:
                    os.remove(yf)
                except OSError as e:
                    logging.error(f"Failed to remove {yf} during reset: {e}")
            # Clear dirty flags so no stale save fires after reload
            self._dirty_resources.clear()
            self._last_dirty_time = 0.0
            # load_config inside the lock so no dirty save interleaves
            self.load_config()
        return True

    def remove_cert(self):
        try:
            os.popen('mv ' + self.configDir + '/cert.pem ' + self.configDir + '/backup/')
            logging.info("Certificate removed")
        except:
            logging.exception("Something went wrong when deleting the certificate")
        generate_certificate(self.argsDict["MAC"], self.argsDict["CONFIG_PATH"])
        return

    def restore_backup(self):
        backup_dir = os.path.join(self.configDir, 'backup')
        if not os.path.isdir(backup_dir):
            raise ValueError("No backup directory found")

        backup_files = glob.glob(os.path.join(backup_dir, '*.yaml'))
        if not backup_files:
            raise ValueError("Backup directory is empty")

        # Validate ALL backup files before touching live config
        for bf in backup_files:
            try:
                with open(bf, 'r', encoding="utf-8") as fp:
                    data = yaml.load(fp, Loader=yaml.FullLoader)
            except Exception as e:
                raise ValueError(f"Backup file {os.path.basename(bf)} is corrupt: {e}") from e
            if data is None:
                raise ValueError(f"Backup file {os.path.basename(bf)} is empty")
            if not isinstance(data, dict):
                raise ValueError(f"Backup file {os.path.basename(bf)} is not a dict")

        # Hold save lock across the entire destructive phase + reload
        with self._save_lock:
            # Delete current yaml files
            for yf in glob.glob(os.path.join(self.configDir, '*.yaml')):
                try:
                    os.remove(yf)
                except OSError as e:
                    logging.error(f"Failed to remove {yf} during restore: {e}")

            # Copy backup files into config dir
            for bf in backup_files:
                shutil.copy2(bf, self.configDir)

            # Clear dirty flags so no stale save fires after reload
            self._dirty_resources.clear()
            self._last_dirty_time = 0.0
            # Reload inside the lock — mutates existing dict in-place
            self.load_config()
        return True

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
        #_write_yaml(self.configDir + "/config_debug.yaml", self.yaml_config["config"])
        #debug = _open_yaml(self.configDir + "/config_debug.yaml")
        debug = deepcopy(self.yaml_config["config"])
        debug["whitelist"] = "privately"
        debug["apiUsers"] = "privately"
        debug["Hue Essentials key"] = "privately"
        debug["users"] = "privately"
        if debug["mqtt"]["enabled"] or "mqttPassword" in debug["mqtt"]:
            debug["mqtt"]["mqttPassword"] = "privately"
        if debug["homeassistant"]["enabled"] or "homeAssistantToken" in debug["homeassistant"]:
            debug["homeassistant"]["homeAssistantToken"] = "privately"
        if debug["hue"]:
            debug["hue"]["hueUser"] = "privately"
            debug["hue"]["hueKey"] = "privately"
        if debug["tradfri"]:
            debug["tradfri"]["psk"] = "privately"
        if debug["alarm"]["enabled"] or "email" in debug["alarm"]:
            debug["alarm"]["email"] = "privately"
        if debug["govee"]["enabled"] or "api_key" in debug["govee"]:
            debug["govee"]["api_key"] = "privately"
        info = {}
        info["OS"] = os.uname().sysname
        info["Architecture"] = os.uname().machine
        info["os_version"] = os.uname().version
        info["os_release"] = os.uname().release
        info["Hue-Emulator Version"] = subprocess.run("stat -c %y HueEmulator3.py", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        info["WebUI Version"] = subprocess.run("stat -c %y flaskUI/templates/index.html", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        info["arguments"] = self.argsDict
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
