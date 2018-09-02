from .colors import *
from .html import *
from .ssdp import *


def nextFreeId(bridge_config, element):
    i = 1
    while (str(i)) in bridge_config[element]:
        i += 1
    return str(i)
