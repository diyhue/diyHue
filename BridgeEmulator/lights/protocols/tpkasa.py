import asyncio
import colorsys
import json
import logging
import socket

from kasa import SmartLightStrip, Discover, TPLinkSmartHomeProtocol

from functions.colors import convert_xy

old_request = None
old_gradient = None
was_off = None
is_gradient = False


# takes up to 10sec. Tested with KL430(have no other device to test)

# atm only works with 2m (no extension)
class KL430LightStrip(SmartLightStrip):

    def __init__(self, host: str) -> None:
        super().__init__(host)

    multi_color = [[0, 0, 0, 0, 0]] * 16

    def build_request(self, command, state, protocol=None):

        """
        :param state: parameters
            examples:
            {"hue": 100, "saturation": 50, "color_temp": 0,
             "brightness": 50, "on_off": 1, "ignore_default": 1}}}  sets light to hsv
            

        :param protocol :Optional smartlife.iot.lighting_effect, smartlife.iot.lightStrip,
        :param command: set_lighting_effect, get_lighting_effect, get_light_state, set_light_state
        """

        if protocol is None:
            if command in ("set_lighting_effect", "get_lighting_effect"):
                protocol = "smartlife.iot.lighting_effect"
            if command in ("get_light_state", "set_light_state"):
                protocol = "smartlife.iot.lightStrip"

        request = {protocol: {command: state}}

        # self.send_debug(1,json.dumps(request).encode())
        bytestream = TPLinkSmartHomeProtocol.encrypt(json.dumps(request))

        return bytestream

    def send_request(self, target, request):
        global old_request
        if old_request == request:
            return
        else:
            old_request = request
        # self.send_debug(1, "sent".encode())
        port = 9999  # Std KAsaPort
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target, port))
        s.sendall(request)
        # print(TPLinkSmartHomeProtocol.decrypt(s.recv(1024)))
        s.close()

    def send_debug(self, target, request):
        port = 7890
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(request, (target, port))

    def create_multi_color(self, pixel, color, brightness=100):
        """Sets a pixel or a group of Pixel to color
        can called multiple times
        :param pixel  pixel or Pixel Group (int or List<int>)
        :param color  Color
        :param brightness
        """
        if isinstance(pixel, int):
            self.multi_color[pixel] = [pixel, pixel, color[0], color[1], brightness, 2501]
        else:
            for index in pixel:
                self.multi_color[index] = [index, index, color[0], color[1], brightness, 2501]

    def create_gradient(self, color: list, brightness):
        """
          Works but not good xD
          creates a multi_color gradiant
          :param color  list of colors for the gradient (5 Colors )
          :param brightness
          """
        segment_sizes = [3, 2, 3, 3]
        fix_points = [0, 4, 7, 11, 15]
        index = 1

        for i in range(0, 4):
            self.create_multi_color(fix_points[i], color[i], brightness)
            # Color dif (shortest way from col1 to col2 )           offsets smaller col by 360
            color_dif = min(abs(color[i][0] - color[i + 1][0]),
                            abs(min(color[i][0], color[i + 1][0]) + 360 - max(color[i][0], color[i + 1][0])))
            sat_dif = color[i + 1][1] - color[i][1]
            clockwise = -1

            if (color[i][0] + color_dif) % 360 == color[i + 1][0]:
                clockwise = 1
            color_dif = color_dif // (segment_sizes[i] + 1)
            sat_dif = sat_dif // (segment_sizes[i] + 1)

            for n in range(index, index + segment_sizes[i]):
                color[i][0] = (color[i][0] + color_dif * clockwise) % 360
                color[i][1] = color[i][1] + sat_dif

                self.create_multi_color(n, color[i], brightness)
                index += 1
            index += 1
        # set last fix_point
        self.create_multi_color(fix_points[4], color[4], brightness)

    def get_gradiant_state(self):
        state = {"on_off": 1}
        state["groups"] = self.multi_color

        return state

    def set_bri(self, bri):

        for i in range(0, len(self.multi_color)):
            self.multi_color[i][4] = bri
        payload = self.get_gradiant_state()
        payload = self.build_request("set_light_state", payload)
        self.send_request(self.host, payload)


def rgb_to_hsv(r, g, b):
    temp = colorsys.rgb_to_hsv(r, g, b)
    h = int(temp[0] * 360)
    s = int(temp[1] * 100)
    v = round(temp[2] * 100 / 255)
    return [h, s, v]


def generate_light_name(base_name, light_nr):
    # Light name can only contain 32 characters
    suffix = ' %s' % light_nr
    return '%s%s' % (base_name[:32 - len(suffix)], suffix)


# Detects only Kl430 but other Kasa devices should work to
def discover(detectedLights):
    logging.debug('Kasa discovery started')
    devices: dict = asyncio.run(Discover.discover(target="192.168.0.255"))

    for device in list(devices.keys()):
        x: KL430LightStrip = devices[device]
        asyncio.run(x.update())

        if x.model.startswith("KL430"):
            ip = device
            name = x.alias
            for x in range(1, 4):
                lightName = name
                protocol_cfg = {"ip": ip, "id": name, "light_nr": x, "model": "KL430", }
                protocol_cfg["points_capable"] = 7
                detectedLights.append({"protocol": "tpkasa", "name": lightName, "modelid": "LCX002",
                                       "protocol_cfg": protocol_cfg})


def translateRange(value, inMin, inMax, outMin, outMax):
    # colortemp 2051 used as indicator for color mode
    value = ((value - inMin) / (inMax - inMin)) * (outMax - outMin)
    out = value + outMin
    if out == 2501:
        return 2500
    return out


def set_light(light, data):
    global is_gradient, old_gradient, was_off
    strip = KL430LightStrip(light.protocol_cfg["ip"])

    gradient = data.get("gradient")
    # strip.send_debug(1,json.dumps({"data":data}).encode())
    # strip.send_debug(1, json.dumps({"light": light.state}).encode())
    if gradient:

        if was_off:
            # strip.send_debug(1,json.dumps({"old_gra":old_gradient}).encode())

            payload = strip.build_request("set_light_state",
                                          {"hue": 0, "saturation": 0, "color_temp": 0, "brightness": 0, "on_off": 1,
                                           "ignore_default": 1})
            strip.send_request(strip.host, payload)
            was_off = False

        is_gradient = True
        colors = []
        point = gradient["points"]

        for i in [0, 1, 2, 3, 4]:
            xy = point[i]["color"]["xy"]
            color = convert_xy(xy["x"], xy["y"], 255)
            hsv = rgb_to_hsv(color[0], color[1], color[2])
            colors.append(hsv)
        if light.state["bri"]:
            strip.create_gradient(colors, int(light.state["bri"] / 2.55))
        else:
            strip.create_gradient(colors, 75)

        payload = strip.get_gradiant_state()
        payload["on_off"] = 1
        old_gradient = payload
        payload = strip.build_request("set_light_state", payload)

        strip.send_request(strip.host, payload)

        return

    payload = {
        "on_off": 1,

    }
    # should work with other Kasa Bulbs to

    for key, value in data.items():

        if key == "on":
            # Saves that's is off
            if not value:
                was_off = True

            # Turns on to the old state
            if value is True and was_off:
                # strip.send_debug(1,json.dumps({"old_gra":old_gradient}).encode())

                payload = strip.build_request("set_light_state",
                                              {"hue": 0, "saturation": 0, "color_temp": 0, "brightness": 0, "on_off": 1,
                                               "ignore_default": 1})
                strip.send_request(strip.host, payload)

                payload = strip.build_request("set_light_state", old_gradient)
                strip.send_request(strip.host, payload)
                was_off = False
                return

            payload["on_off"] = value

        elif key == "bri":
            payload["brightness"] = int(value / 2.55)
            if is_gradient:
                strip.set_bri(payload["brightness"])
                return

        elif key == "ct":
            is_gradient = False
            # color temp == 2501 indicates colorMode (found no other way)
            payload["color_temp"] = round(translateRange(value, 500, 153, 2500, 6500))
            payload["hue"] = 0
            payload["brightness"] = int(light.state["bri"] / 2.55)

        elif key == "alert" and value != "none":
            payload["brightness"] = 100

    data = strip.build_request("set_light_state", payload)
    strip.send_request(strip.host, data)


"""async def get_state(strip):

    await strip.update()
    s = await strip.get_light_state()
    groups = s["groups"]
    state = {}
    if s["on_off"] == 1:
        state["on"] = True
    else:
        state["on"] = False
    if len(groups) == 1:
        if groups[0][5] == 2501:
            state["mode"] = "hue"
            state["color"] = [groups[0][2], groups[0][3], groups[0][4]]

        else:
            state["mode"] = "ct"
            state["ct"] = groups[0][5]
            state["bri"] = groups[0][4]

    else:
        state["mode"] = "gradiant"
        state["bri"] = groups[0][4]
        gradient = []
        fix_Points = [0, 4, 7, 11, 15]
        for point in fix_Points:
            for color in groups:

                if color[0] <= point and color[1] >= point:
                    gradient.append([color[2],color[3],color[4]])
        state["gradient"]=gradient


    return state"""


def get_light_state(light):
    return {}


"""strip = KL430LightStrip(light.protocol_cfg["ip"])
    light_state = asyncio.run(get_state(strip))
    state={}
    if light_state["on"] == True:
        state["on"] = True
    else:
        state["on"] = False
        return state
    if light_state["mode"] == "ct":
        state["colormode"] = "ct"
        state["ct"] = round(translateRange(light_state["ct"], 2500, 6500,500, 135))
        state["bri"] = round(light_state["bri"] * 2.55)
    if light_state["mode"] == "hue":
        state["colormode"] = "hs"
        state["hue"] = light_state["color"][0]
        state["sat"] = light_state["color"][1]
        state["bri"] = round(light_state["color"][2] * 2.55)
    if light_state["mode"] == "gradiant":
        pass
        #state["bri"]
        #state["xy"]
        #state["colormode"] = "xy"
    return state"""
