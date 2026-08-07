import logManager
import asyncio
from functions.colors import convert_xy, convert_rgb_xy
logging = logManager.logger.get_logger(__name__)
Connections = {}

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

### libhueble ###
### https://github.com/alexhorn/libhueble/ ###
from bleak import BleakClient, BleakScanner
from struct import pack, unpack

# device name as an ASCII string
CHAR_NAME = '97fe6561-0003-4f62-86e9-b71ee2da3d22'
# model number as an ASCII string
CHAR_MODEL = '00002a24-0000-1000-8000-00805f9b34fb'
# power state (0 or 1)
CHAR_POWER = '932c32bd-0002-47a2-835a-a8d455b859dd'
# brightness (1 to 254)
CHAR_BRIGHTNESS = '932c32bd-0003-47a2-835a-a8d455b859dd'
# color (CIE XY coordinates converted to two 16-bit little-endian integers)
CHAR_COLOR = '932c32bd-0005-47a2-835a-a8d455b859dd'
# temperature
CHAR_TEMPERATURE = '932c32bd-0004-47a2-835a-a8d455b859dd'

# Bluetooth UUID for Hue lights
HUE_SERVICE_IDENTIFIER_UUID = "0000fe0f-0000-1000-8000-00805f9b34fb"
DISCOVERY_TIMEOUT_SEC = 5

class Lamp(object):
    """A wrapper for the Philips Hue BLE protocol"""

    def __init__(self, address):
        self.address = address
        self.client = None
        self.name = None
        self.model = None

    @property
    def is_connected(self):
        return self.client and self.client.is_connected

    async def connect(self):
        # reinitialize BleakClient for every connection to avoid errors
        self.client = BleakClient(self.address, pair=True)
        logging.debug(f"Connecting to Hue Bluetooth light with address: {self.address}")
        await self.client.connect()
        self.name = await self.get_name()
        self.model = await self.get_model()
        return self.client.is_connected

    async def disconnect(self):
        try:
            await self.client.disconnect()
        except Exception as e:
            logging.error(f"Error disconnecting from Hue Bluetooth light: {e}")
        finally:
            self.client = None
            Connections[self.address] = None

    async def get_name(self):
        """Returns the device name"""
        name = await self.client.read_gatt_char(CHAR_NAME)
        return name.decode('ascii')

    async def get_model(self):
        """Returns the model string"""
        model = await self.client.read_gatt_char(CHAR_MODEL)
        return model.decode('ascii')

    async def get_power(self):
        """Gets the current power state"""
        power = await self.client.read_gatt_char(CHAR_POWER)
        return bool(power[0])

    async def set_power(self, on):
        """Sets the power state"""
        await self.client.write_gatt_char(CHAR_POWER, bytes([1 if on else 0]), response=True)

    async def get_brightness(self):
        """Gets the current brightness as a float between 0.0 and 1.0"""
        brightness = await self.client.read_gatt_char(CHAR_BRIGHTNESS)
        return brightness[0] / 255

    async def set_brightness(self, brightness):
        """Sets the brightness from a float between 0.0 and 1.0"""
        await self.client.write_gatt_char(CHAR_BRIGHTNESS, bytes([max(min(int(brightness * 255), 254), 1)]), response=True)

    async def get_color_xy(self):
        """Gets the current XY color coordinates as floats between 0.0 and 1.0"""
        buf = await self.client.read_gatt_char(CHAR_COLOR)
        x, y = unpack('<HH', buf)
        return x / 0xFFFF, y / 0xFFFF

    async def set_color_xy(self, x, y):
        """Sets the XY color coordinates from floats between 0.0 and 1.0"""
        buf = pack('<HH', int(x * 0xFFFF), int(y * 0xFFFF))
        await self.client.write_gatt_char(CHAR_COLOR, buf, response=True)

    async def get_color_rgb(self):
        """Gets the RGB color as floats between 0.0 and 1.0"""
        brightness = self.get_brightness()
        x, y = await self.get_color_xy()
        return convert_xy(x, y, brightness)

    async def set_color_rgb(self, r, g, b):
        """Sets the RGB color from floats between 0.0 and 1.0"""
        x, y = convert_rgb_xy(r, g, b)
        await self.set_color_xy(x, y)

    def supports_colour_xy(self):
        return self.client.services.get_characteristic(CHAR_COLOR) is not None
    
    def supports_colour_temp(self):
        return self.client.services.get_characteristic(CHAR_TEMPERATURE) is not None
    
    def supports_brightness(self):
        return self.client.services.get_characteristic(CHAR_BRIGHTNESS) is not None

async def connect(light, reconnect=False):
    ip = light.protocol_cfg["ip"]
    if ip in Connections and not reconnect:
        c = Connections[ip]
    else:
        c = Lamp(ip)
        await c.connect()
        Connections[ip] = c
    return c

async def set_light_async(light, data, retry=False):
    c = await connect(light)
    try:
        for key, value in data.items():
            if key == "on":
                await c.set_power(value)
            if key == "bri":
                await c.set_brightness(value / 254)
            if key == "xy":
                # not all models support color
                try:
                    color = convert_xy(value[0], value[1], light.state["bri"])
                    await c.set_color_rgb(color[0] / 254, color[1] / 254, color[2] / 254)
                except Exception as e:
                    logging.error(e)
    except:
        # reconnect and try again once
        await connect(light, reconnect=True)
        if not retry:
            await set_light_async(light, data, retry=True)

def set_light(light, data):
    loop.run_until_complete(set_light_async(light, data))


async def get_light_state_async(address, retry=False):
    state = {"on": False}
    try:
        bl_light = await connect(address)
        state["on"] = await bl_light.get_power()
        state["xy"] = await bl_light.get_color_xy()
        if bl_light.supports_colour_xy():
            state["colormode"] = "xy"
        elif bl_light.supports_colour_temp():
            state["colormode"] = "ct"
        elif bl_light.supports_brightness():
            state["bri"] = await bl_light.get_brightness()
    except Exception as e:
        logging.error(e)
        return { 'reachable': False }
    return state

def get_light_state(light):
    return loop.run_until_complete(get_light_state_async(light))

async def discover_lights_async():
    bl_lights = []
    devices_and_adv_data_map = await BleakScanner.discover(DISCOVERY_TIMEOUT_SEC, return_adv=True)
    devices_and_adv_data = devices_and_adv_data_map.values()
    logging.debug(f"Discovered {len(devices_and_adv_data)} total bluetooth devices")
    for i, (d, adv) in enumerate(devices_and_adv_data):
        if (HUE_SERVICE_IDENTIFIER_UUID in adv.service_uuids and d not in bl_lights):
            logging.debug(f"Discovered Hue bluetooth device: {d} with advertisements: {adv}")
            bl_lights.append(d)
    connected_lights = []
    for bl_light in map(lambda l: Lamp(l.address), bl_lights):
        is_connected = await bl_light.connect()
        if is_connected:
            connected_lights.append(bl_light)
        else:
            logging.error(f"Unable to connect to address {bl_light.address}")

    return connected_lights

def discover(detectedLights):
    logging.debug("hue_bl: <discover> invoked!")
    try:
        lights = asyncio.run(discover_lights_async())
        if len(lights) > 0:
            logging.debug(f"Discovered {len(lights)} Hue bluetooth light(s)")
        for l in lights:
            detectedLights.append({"protocol": "hue_bl", "name": l.name, "modelid": l.model, "protocol_cfg": {"ip": l.address, "modelid": l.model, "id": l.address, "uniqueid": l.address}})        
    except Exception as e:
        logging.error(f"Error connecting to BLE light: {e}")

    logging.debug(f"detected_lights: {detectedLights}")
