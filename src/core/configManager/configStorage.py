import json
import os
import logManager
import configManager
from datetime import datetime
from subprocess import call
from pathlib import Path

logging = logManager.logger.get_logger(__name__)
# TODO: add empty file to config dir and check for it, if found, notify user to mount the config dir to ensure config is not lost

class configStorage:
    core_config = None
    bridge_config = None
    # runtime_config = None # left here for the future as we dont actually want to save the runtime config for now
    projectDir = '/diyhue'  # cwd = os.path.split(os.path.abspath(__file__))[0]
    configDir = '/config'

    def __init__(self):
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)
        self.load_core()

    @staticmethod
    def _generate_certificate(mac):
        logging.info("Generating certificate")
        call(["/bin/bash", "/diyhue/genCert.sh", mac])
        logging.info("Certificate created")

    @staticmethod
    def _open_json(path):
        with open(path, 'r', encoding="utf-8") as fp:
            return json.load(fp)

    @staticmethod
    def _write_json(path, contents):
        with open(path, 'w', encoding="utf-8") as fp:
            json.dump(contents, fp, sort_keys=True, indent=4, separators=(',', ': '))

    def get_path(self, file, project=False, config=False): #defaulting to config for now...
        if project:
            return Path(self.projectDir, file).as_posix()
        else:
            return Path(self.configDir, file).as_posix()

    def _generate_new_config(self):
        self.bridge_config = {}
        # self.runtime_config = {}

    def _update_core_config(self):  # prepares core config for saving
        self.core_config = {}
        self.core_config["bridge_config"] = self.bridge_config
        # self.core_config["runtime_config"] = self.runtime_config

    def _save_core(self, backup=False):  # saves core config as is, use caution
        if backup:
            filename = "config--backup-" + datetime.now().strftime("%Y-%m-%d--%H-%M-%S-%f") + ".json"
        else:
            filename = "config.json"
        self._write_json(self.get_path(filename, config=True), self.core_config)
        return filename

    def load_core(self):
        if os.path.exists(self.get_path("config.json", config=True)):
            self.core_config = self._open_json(self.get_path("config.json", config=True))
            logging.info("Core config found")
            try:
                self.bridge_config = self.core_config["bridge_config"]
                # self.runtime_config = self.core_config["runtime_config"]
            except Exception:
                logging.warning("Core config could not be imported, overwriting current config with defaults")
                self.reset_core()
        else:
            logging.info("No configuration file detected, creating new config")
            self._generate_new_config()
            self.save_latest_core()

    def save_latest_core(self, backup=False):
        self._update_core_config()
        return self._save_core(backup)

    def reset_core(self):
        self._save_core(True) #first make a backup of what was read from the disk
        filename = self.save_latest_core(True) #then make a backup of the in-memory config
        self._generate_new_config()
        self.save_latest_core()
        return filename

    def initialize_certificate(self, reset=False):  # resetting of certificates is never used currently, maybe add to reset core?
        if reset:
            filename = "cert--backup-" + datetime.now().strftime("%Y-%m-%d--%H-%M-%S-%f") + ".pem"
            os.rename(self.get_path("cert.pem", config=True), self.get_path(filename, config=True))
        if not os.path.isfile(self.get_path("cert.pem", config=True)):
            self._generate_certificate(configManager.runtimeConfig.arg["FULLMAC"])
