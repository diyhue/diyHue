import asyncio
import colorsys
import json
import logging
import socket

from kasa import SmartLightStrip, Discover, TPLinkSmartHomeProtocol

from functions.colors import convert_xy

import logManager

old_request = None  # Globle works bc to diff. lights have diff requests

# Dosnt work as globle if more then 1 light exist
was_off = None

logging = logManager.logger.get_logger(__name__)



# takes up to 10sec. Tested with KL430(have no other device to test)

# atm only works with 2m (no extension)
class KL430LightStrip(SmartLightStrip):

    def __init__(self, host: str) -> None:
        super().__init__(host)


'''def create_multi_color(pixel, color, brightness=100):
    """Sets a pixel or a group of Pixel to color
    can called multiple times
    :param pixel  pixel or Pixel Group (int or List<int>)
    :param color  Color
    :param brightness
    """
    if isinstance(pixel, int):
        multi_color[pixel] = [pixel, pixel, color[0], color[1], brightness, 2501]
    else:
        for index in pixel:
            multi_color[index] = [index, index, color[0], color[1], brightness, 2501]'''


def create_gradient(color: list, brightness):
    multi_color = [[0, 0, 0, 0, 0, 0]] * 16
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
        multi_color[fix_points[i]] = [fix_points[i],fix_points[i],color[i][0], color[i][1], brightness,2501]

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

            multi_color[n] = [n, n, color[i][0], color[i][1], brightness,2501]
            index += 1
        index += 1
    # set last fix_point
    multi_color[fix_points[4]] = [fix_points[4],fix_points[4],color[4][0], color[4][1], brightness,2501]

    return multi_color

def get_gradiant_state(multi_color):
    state = {"on_off": 1}
    state["groups"] = multi_color

    return state


def set_bri(multi_color, bri, ip):
    for i in range(0, len(multi_color)):
        multi_color[i][4] = bri
    payload = get_gradiant_state(multi_color)
    payload = build_request("set_light_state", payload)
    send_request(ip, payload)


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
                protocol_cfg = {"ip": ip, "id": name, "light_nr": x, "model": "KL430", "old_state": None}
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


def build_request(command, state, protocol=None):
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

    #send_debug("192.168.0.201", json.dumps(request).encode())
    bytestream = TPLinkSmartHomeProtocol.encrypt(json.dumps(request))

    return bytestream


def send_request(target, request):
    global old_request
    if old_request == request:
        return
    else:
        old_request = request

    port = 9999  # Std KAsaPort
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((target, port))
    s.sendall(request)
    # print(TPLinkSmartHomeProtocol.decrypt(s.recv(1024)))
    s.close()


def send_debug(target, request):
    port = 7890
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(request, (target, port))


def set_light(light, data):
    # strip = KL430LightStrip(light.protocol_cfg["ip"])

    gradient = data.get("gradient")

    if gradient:

        light.state["is_gradient"] = True
        # Turnes on Light with bri 0 if it was off
        if not light.state["is_on"]:

            payload = build_request("set_light_state",
                                    {"hue": 0, "saturation": 0, "color_temp": 0, "brightness": 0, "on_off": 1,
                                     "ignore_default": 1})
            send_request(light.protocol_cfg["ip"], payload)
            light.state["is_on"] = True


        colors = []
        point = gradient["points"]

        for i in [0, 1, 2, 3, 4]:
            xy = point[i]["color"]["xy"]
            color = convert_xy(xy["x"], xy["y"], 255)
            hsv = rgb_to_hsv(color[0], color[1], color[2])
            colors.append(hsv)
        if light.state["bri"]:
            colorArr = create_gradient(colors, int(light.state["bri"] // 2.55))
        else:
            colorArr = create_gradient(colors, 75)


        light.state["multi_color"] = colorArr
        payload = get_gradiant_state(colorArr)
        payload["on_off"] = 1
        light.state["old_payload"] = payload
        payload = build_request("set_light_state", payload)



        send_request(light.protocol_cfg["ip"], payload)

        return

    payload = {
        "on_off": 1,
    }
    # should work with other Kasa Bulbs to

    for key, value in data.items():

        if key == "on":

            # Turns on to the old state
            if value is True and not light.state["is_on"]:
                # strip.send_debug(1,json.dumps({"old_gra":old_gradient}).encode())

                payload = build_request("set_light_state",
                                        {"hue": 0, "saturation": 0, "color_temp": 0, "brightness": 0, "on_off": 1,
                                         "ignore_default": 1})
                send_request(light.protocol_cfg["ip"], payload)

                payload = build_request("set_light_state", light.state["old_payload"])
                send_request(light.protocol_cfg["ip"], payload)
                light.state["is_on"] = True
                return

            payload["on_off"] = value
            light.state["is_on"] = value

        elif key == "bri":
            payload["brightness"] = int(value / 2.55)
            if light.state["is_gradient"]:
                set_bri(light.state["multi_color"], payload["brightness"], light.protocol_cfg["ip"])
                return

        elif key == "ct":
            light.state["is_on"] = True
            light.state["is_gradient"] = False
            # color temp == 2501 indicates colorMode (found no other way)
            payload["color_temp"] = round(translateRange(value, 500, 153, 2500, 6500))
            payload["hue"] = 0
            payload["brightness"] = int(light.state["bri"] / 2.55)
            light.state["old_payload"] = payload


        elif key == "alert" and value != "none":
            payload["brightness"] = 100

    data = build_request("set_light_state", payload)
    send_request(light.protocol_cfg["ip"], data)


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
