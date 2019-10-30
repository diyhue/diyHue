def nextFreeId(bridge_config, element):
    i = 1
    while (str(i)) in bridge_config[element]:
        i += 1
    return str(i)

# Define light defininitions for discovery features and adding device data to config
light_types = {}
light_types["Tasmota"] = {"type": "Extended color light", "swversion": "1.46.13_r26312"}
light_types["Tasmota"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}

light_types["ESPHome-RGB"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
light_types["ESPHome-RGB"]["state"] = {"on": False, "bri": 254, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}
light_types["ESPHome-RGB"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["ESPHome-Dimmable"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
light_types["ESPHome-Dimmable"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
light_types["ESPHome-Dimmable"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["ESPHOME-Toggle"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12", "manufacturername": "ESPHome"}
light_types["ESPHOME-Toggle"]["state"] = {"on": False, "alert": "none", "reachable": True}
light_types["ESPHOME-Toggle"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["LCT015"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
light_types["LCT015"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}
light_types["LCT015"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}
light_types["LCT015"]["capabilities"] = {"certified": True, "control": {"mindimlevel": 1000, "maxlumen": 806, "ct":{"min": 153, "max": 500}}}
light_types["LCT015"]["streaming"] = {"renderer": True, "proxy": True}


light_types["LST002"] = {"type": "Color light", "swversion": "5.127.1.26581"}
light_types["LST002"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}

light_types["LWB010"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
light_types["LWB010"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
light_types["LWB010"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["LTW001"] = {"type": "Color temperature light", "swversion": "1.46.13_r26312"}
light_types["LTW001"]["state"] = {"on": False, "colormode": "ct", "alert": "none", "reachable": True, "bri": 254, "ct": 230}

light_types["Plug 01"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12"}
light_types["Plug 01"]["state"] = {"on": False, "alert": "none", "reachable": True}
