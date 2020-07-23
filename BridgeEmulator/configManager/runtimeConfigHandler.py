from dataclasses import dataclass, field
from configManager.argumentHandler import parse_arguments


def _empty_dict():
    return {}


def _dxState_default():
    return {"sensors": {}, "lights": {}, "groups": {}}


def _get_args():
    return parse_arguments()


@dataclass
class Config:
    newLights: dict = field(default_factory=_empty_dict)
    dxState: dict = field(default_factory=_dxState_default())
    arg: dict = field(default_factory=_get_args())
