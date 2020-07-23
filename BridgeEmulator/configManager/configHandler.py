from dataclasses import dataclass
import datetime
import os
import json
import logging


def _open_json(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return json.load(fp)


def _write_json(path, contents):
    with open(path, 'w', encoding="utf-8") as fp:
        json.dump(contents, fp, sort_keys=True, indent=4, separators=(',', ': '))


@dataclass
class Config:
    json_config: dict = None
    projectDir: str = '/opt/hue-emulator'  # cwd = os.path.split(os.path.abspath(__file__))[0]
    configDir: str = projectDir + '/config'

    def load_config(self):
        try:
            if os.path.exists(self.configDir):
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
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)
        path = self.configDir + '/' + filename
        _write_json(path, self.json_config)


