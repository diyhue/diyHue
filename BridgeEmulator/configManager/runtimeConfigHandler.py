from dataclasses import dataclass
from configManager.argumentHandler import parse_arguments


@dataclass
class Config:
    newLights: dict = None
    arg: dict = None

    def populate(self):
        self.newLights = {}
        self.arg = parse_arguments()
