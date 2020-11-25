from abc import ABC, abstractmethod
from typing import Tuple


class BaseDeviceProtocol(ABC):

    @abstractmethod
    def supported_devices(self):
        """
        Returns dictionary of supported device types
        return {
            const.PROTOCOL_BULB_RGB,
            const.PROTOCOL_BULB_RGBW
        }
        :return: dict
        """
        raise NotImplementedError()

    @abstractmethod
    def discover(self):
        raise NotImplementedError()

    @abstractmethod
    def turn_on(self, bri, kelvin, red, green, blue) -> None:
        raise NotImplementedError()

    @abstractmethod
    def turn_off(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_is_on(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def on_loop(self):
        raise NotImplementedError()

class LightProtocol(BaseDeviceProtocol, ABC):

    @abstractmethod
    def set_brightness(self, bri) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_brightness(self) -> int:
        raise NotImplementedError()

class rgbLightProtocol(LightProtocol, ABC):

    @abstractmethod
    def set_color(self, red, green, blue) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_color(self) -> Tuple[int, int, int]:
        """
        Get rgb value of light.
        :return: red, green, blue
        """
        raise NotImplementedError()
