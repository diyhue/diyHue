from abc import ABC, abstractmethod
from typing import Tuple


class BaseDeviceProtocol(ABC):

    @abstractmethod
    def discover(self):
        raise NotImplementedError("Method must be overridden!")

    @abstractmethod
    def turn_on(self, bri, kelvin, red, green, blue) -> None:
        raise NotImplementedError("Method must be overridden!")

    @abstractmethod
    def turn_off(self) -> None:
        raise NotImplementedError("Method must be overridden!")

    @abstractmethod
    def get_is_on(self) -> bool:
        raise NotImplementedError("Method must be overridden!")

    @abstractmethod
    def on_loop(self):
        raise NotImplementedError("Method must be overridden!")

class LightProtocol(BaseDeviceProtocol, ABC):

    @abstractmethod
    def set_brightness(self, bri) -> None:
        raise NotImplementedError("Method must be overridden!")

    @abstractmethod
    def get_brightness(self) -> int:
        raise NotImplementedError("Method must be overridden!")

class rgbLightProtocol(LightProtocol, ABC):

    @abstractmethod
    def set_color(self, red, green, blue) -> None:
        raise NotImplementedError("Method must be overridden!")

    @abstractmethod
    def get_color(self) -> Tuple[int, int, int]:
        """
        Get rgb value of light.
        :return: red, green, blue
        """
        raise NotImplementedError("Method must be overridden!")
