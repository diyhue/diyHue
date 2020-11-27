import json
import logManager
import configManager
configOperations = configManager.configOperations
logging = logManager.logger.get_logger(__name__)


def _open_json(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return json.load(fp)


class Config:
    _json_config = None

    def __init__(self, bridge_config):
        self.json_config = bridge_config
        self.load_config()

    @property
    def json_config(self):
        return self._json_config

    @json_config.setter
    def json_config(self, value):
        self._json_config = value
        self.save_config()

    @json_config.deleter
    def json_config(self):
        del self._json_config

    def load_config(self):
        if not self.json_config:
            logging.info("Bridge config was empty, creating new default config")
            self.save_config(True) # TODO: convert json to dynamically generated default config
            self.json_config = _open_json(configManager.coreConfig.projectDir + '/default-config.json')
            self.save_config()

    def save_config(self, backup=False):
        logging.debug("Saving config!")
        configManager.coreConfig.bridge_config = self.json_config
        return configManager.coreConfig.save_latest_core(backup)

    def reset_config(self):
        backup = configManager.coreConfig.reset_core()
        self.json_config = configManager.coreConfig.bridge_config  # should be blank now
        self.load_config()
        return backup

    def write_args(self, args):
        self.json_config = configOperations.write_args(args, self.json_config)

    def generate_security_key(self):
        self.json_config = configOperations.generate_security_key(self.json_config)

    def sanitizeBridgeScenes(self):
        self.json_config = configOperations.sanitizeBridgeScenes(self.json_config)

    def updateConfig(self):
        self.json_config = configOperations.updateConfig(self.json_config)

    def resourceRecycle(self):  # was originally in a new thread/not sure if necessary
        recycled = configOperations.resourceRecycle(self.json_config)

        def set_new():
            self.json_config = recycled
            logging.info("done recycling")

        from threading import Timer
        t = Timer(5.0, set_new).start()  # give time to application to delete all resources, then start the cleanup

    def update_swversion(self):
        self.json_config = configOperations.update_swversion(self.json_config)
