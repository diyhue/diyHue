from dataclasses import dataclass
from configManager.argumentHandler import parse_arguments


@dataclass
class Config:
    newLights: dict = None
    dxState: dict = None
    arg: dict = None

    def populate(self):
        self.newLights = {}
        self.dxState = {"sensors": {}, "lights": {}, "groups": {}}
        self.arg = parse_arguments()
