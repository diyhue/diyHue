from .GenericProtocol import BaseDeviceProtocol
from typing import cast


class ToggleableDevice:
    is_on = False

    def __init__(self, protocol):
        if issubclass(BaseDeviceProtocol, protocol):
            self.protocol = cast(BaseDeviceProtocol, protocol)
        else:
            raise TypeError("Protocol must inherit BaseDeviceProtocol!")

    def turn_on(self, bri=None, kelvin=None, red=None, green=None, blue=None) -> None:
        self.protocol.turn_on(bri, kelvin, red, green, blue)
        self.is_on = True

    def turn_off(self) -> None:
        self.protocol.turn_off()
        self.is_on = False

    def _get_is_on(self) -> None:
        self.is_on = self.protocol.get_is_on()

    def get_state(self) -> dict:
        return {"is_on": self.is_on}

    def on_loop(self) -> None:
        """
        Protocol will update a cached state if necessary. If no caching is done at a protocol level,
        this method can be passed by the protocol.
        :return: None
        """
        self.protocol.on_loop()
        self._get_is_on()
