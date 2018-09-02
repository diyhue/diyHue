import logging
import socket

from functions import light_types, nextFreeId


def discover(bridge_config, new_lights):
    group = ("239.255.255.250", 1982)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: 239.255.255.250:1982',
        'MAN: "ssdp:discover"',
        'ST: wifi_bulb'])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(3)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.sendto(message.encode(), group)
    while True:
        try:
            response = sock.recv(1024).decode('utf-8').split("\r\n")
            properties = {"rgb": False, "ct": False}
            for line in response:
                if line[:2] == "id":
                    properties["id"] = line[4:]
                elif line[:3] == "rgb":
                    properties["rgb"] = True
                elif line[:2] == "ct":
                    properties["ct"] = True
                elif line[:8] == "Location":
                    properties["ip"] = line.split(":")[2][2:]
                elif line[:4] == "name":
                    properties["name"] = line[6:]
            device_exist = False
            for light in bridge_config["lights_address"].keys():
                if bridge_config["lights_address"][light]["protocol"] == "yeelight" and  bridge_config["lights_address"][light]["id"] == properties["id"]:
                    device_exist = True
                    bridge_config["lights_address"][light]["ip"] = properties["ip"]
                    logging.debug("light id " + properties["id"] + " already exist, updating ip...")
                    break
            if (not device_exist):
                light_name = "YeeLight id " + properties["id"][-8:] if properties["name"] == "" else properties["name"]
                logging.debug("Add YeeLight: " + properties["id"])
                modelid = "LWB010"
                if properties["rgb"]:
                    modelid = "LCT015"
                elif properties["ct"]:
                    modelid = "LTW001"
                new_light_id = nextFreeId(bridge_config, "lights")
                bridge_config["lights"][new_light_id] = {"state": light_types[modelid]["state"], "type": light_types[modelid]["type"], "name": light_name, "uniqueid": "4a:e0:ad:7f:cf:" + str(random.randrange(0, 99)) + "-1", "modelid": modelid, "manufacturername": "Philips", "swversion": light_types[modelid]["swversion"]}
                new_lights.update({new_light_id: {"name": light_name}})
                bridge_config["lights_address"][new_light_id] = {"ip": properties["ip"], "id": properties["id"], "protocol": "yeelight"}


        except socket.timeout:
            logging.debug('Yeelight search end')
            sock.close()
            break
