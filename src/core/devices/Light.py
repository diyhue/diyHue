from .ToggleableDevice import ToggleableDevice
from .GenericProtocol import LightProtocol
from typing import cast


class Light(ToggleableDevice):
    brightness = 0  # brightness value from 0-100

    def __init__(self, protocol):
        super().__init__(protocol)
        self.protocol = cast(LightProtocol, protocol)

    def set_brightness(self, bri) -> None:
        self.protocol.set_brightness(bri)
        self.brightness = bri

    def _get_brightness(self) -> None:
        self.brightness = self.protocol.get_brightness()

    def get_state(self) -> dict:
        toggle_state = super(Light, self).get_state()
        light_state = {"brightness": self.brightness}
        return {**toggle_state, **light_state}

    def on_loop(self):
        super(Light, self).on_loop()
        self._get_brightness()

