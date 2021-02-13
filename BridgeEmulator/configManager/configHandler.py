from configManager import configInit
from datetime import datetime
import os
import json
import logManager

logging = logManager.logger.get_logger(__name__)

def _open_json(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return json.load(fp)


def _write_json(path, contents):
    with open(path, 'w', encoding="utf-8") as fp:
        json.dump(contents, fp, sort_keys=True, indent=4, separators=(',', ': '))


class Config:
    json_config = None
    projectDir = '/opt/hue-emulator'  # cwd = os.path.split(os.path.abspath(__file__))[0]
    configDir = projectDir + '/config'

    def __init__(self):
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)

    def load_config(self):
        try:
            if os.path.exists(self.configDir + "/config.json"):
                self.json_config = _open_json(self.configDir + "/config.json")
                logging.info("Config loaded")
            else:
                logging.info("Config not found, creating new config from default settings")
                self.json_config = _open_json(self.projectDir + '/default-config.json')
                self.save_config()
        except Exception:
            logging.exception("CRITICAL! Config file was not loaded")
            raise SystemExit("CRITICAL! Config file was not loaded")

    def save_config(self, backup=False):
        if backup:
            filename = "config--backup-" + datetime.now().strftime("%Y-%m-%d--%H-%m-%S") + ".json"
        else:
            filename = "config.json"
        path = self.configDir + '/' + filename
        _write_json(path, self.json_config)
        return filename

    def reset_config(self):
        backup = self.save_config(True)
        try:
            os.remove(self.configDir + "/config.json")
        except:
            logging.exception("Something went wrong when deleting the config")
        self.load_config()
        return backup

    def write_args(self, args):
        self.json_config = configInit.write_args(args, self.json_config)

    def generate_security_key(self):
        self.json_config = configInit.generate_security_key(self.json_config)

    def sanitizeBridgeScenes(self):
        self.json_config = configInit.sanitizeBridgeScenes(self.json_config)

    def updateConfig(self):
        self.json_config = configInit.updateConfig(self.json_config)
