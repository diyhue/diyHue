from .Light import Light
from .GenericProtocol import rgbLightProtocol
from typing import cast


class rgbLight(Light):
    red = 0
    green = 0
    blue = 0

    def __init__(self, protocol):
        super().__init__(protocol)
        self.protocol = cast(rgbLightProtocol, protocol)

    def set_color(self, red, green, blue) -> None:
        self.protocol.set_color(red, green, blue)
        self.red = red
        self.green = green
        self.blue = blue

    def get_state(self) -> dict:
        light_state = super(rgbLight, self).get_state()
        rgb_state = {"red": self.red, "green": self.green, "blue": self.blue}
        return {**light_state, **rgb_state}

    def _get_color(self) -> None:
        self.red, self.green, self.blue = self.protocol.get_color()

    def on_loop(self) -> None:
        super(rgbLight, self).on_loop()
        self._get_color()
