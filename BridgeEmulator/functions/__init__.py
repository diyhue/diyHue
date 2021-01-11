def nextFreeId(bridge_config, element):
    i = 1
    while (str(i)) in bridge_config[element]:
        i += 1
    return str(i)

# Define light defininitions for discovery features and adding device data to config
light_types = {}
light_types["Tasmota"] = {"type": "Extended color light", "swversion": "1.46.13_r26312"}
light_types["Tasmota"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}

light_types["Shelly"] = {"type": "shelly1", "swversion": "1.46.13_r26312"}
light_types["Shelly"]["state"] = {"on": False, "alert": "none", "reachable": True}

light_types["ESPHome-RGB"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
light_types["ESPHome-RGB"]["state"] = {"on": False, "bri": 254, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}
light_types["ESPHome-RGB"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["ESPHome-Dimmable"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
light_types["ESPHome-Dimmable"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
light_types["ESPHome-Dimmable"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["ESPHOME-Toggle"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12", "manufacturername": "ESPHome"}
light_types["ESPHOME-Toggle"]["state"] = {"on": False, "alert": "none", "reachable": True}
light_types["ESPHOME-Toggle"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["LCT001"] = {"type":"Extended color light", "manufacturername": "Signify Netherlands B.V.", "modelid": "LCT001"}
light_types["LCT001"]["state"] = {"alert": "none", "bri":0, "colormode": "xy", "effect": "none","hue": 0, "mode": "homeautomation","on": False,"reachable": True, "sat": 0,"xy": [0.408,0.517]}
light_types["LCT001"]["config"] = {"archetype": "sultanbulb","direction": "omnidirectional","function": "mixed","startup": {"configured": True, "mode": "powerfail"}}
light_types["LCT001"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.675,0.322],[0.409,0.518],[0.167,0.04]],"colorgamuttype": "B","ct": {"max": 500,"min": 153},"maxlumen": 600,"mindimlevel": 5000},"streaming": {"proxy": False,"renderer": True}},

light_types["LCT015"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
light_types["LCT015"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
light_types["LCT015"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}
light_types["LCT015"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]],"colorgamuttype": "C","ct": {"max": 500,"min": 153},"maxlumen": 800,"mindimlevel": 1000},"streaming": {"proxy": False,"renderer": True}}

light_types["LST002"] = {"type": "Color light", "swversion": "5.127.1.26581"}
light_types["LST002"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
light_types["LST002"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.704,0.296],[0.2151,0.7106],[0.138,0.08]],"colorgamuttype": "A","maxlumen": 200,"mindimlevel": 10000},"streaming": {"proxy": False,"renderer": True}}
light_types["LST002"]["config"] = {"archetype": "huelightstrip","direction": "omnidirectional","function": "mixed"}

# Duplicate light strips
light_types["LST001"] = light_types["LST002"]
light_types["LST003"] = light_types["LST002"]
light_types["LCL001"] = light_types["LST002"]
light_types["LCL002"] = light_types["LST002"]


light_types["LWB010"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
light_types["LWB010"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
light_types["LWB010"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["LTW001"] = {"type": "Color temperature light", "swversion": "1.46.13_r26312"}
light_types["LTW001"]["state"] = {"on": False, "colormode": "ct", "alert": "none", "mode": "homeautomation", "reachable": True, "bri": 254, "ct": 230}
light_types["LTW001"]["capabilities"] = {"certified": True,"control": {"mindimlevel": 1000,"maxlumen": 806,"ct": {"min": 153,"max": 454}},"streaming": {"renderer": False,"proxy": False}}

light_types["Plug 01"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12"}
light_types["Plug 01"]["state"] = {"on": False, "alert": "none", "reachable": True}
light_types["Plug 01"]["config"] = {"archetype": "adapter", "function": "mixed", "direction": "omnidirectional"}

# The Home Assistant below mimic Hue Bulbs to provide better compatability
# HomeAssistant-RGB is a Hue White + Colour Ambience
light_types["HomeAssistant-RGB"] = {"type": "Extended color light", "swversion": "1.50.2_r30933", "manufacturername": "Signify Netherlands B.V.", "modelid" : "LCT015", "productname": "Hue color lamp", "productid": "Philips-LCT015-1-A19ECLv5"}
light_types["HomeAssistant-RGB"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}
light_types["HomeAssistant-RGB"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]],"colorgamuttype": "C","ct": {"max": 500,"min": 153},"maxlumen": 800,"mindimlevel": 1000},"streaming": {"proxy": True,"renderer": True}}
light_types["HomeAssistant-RGB"]["state"] = {"on": False, "bri": 0, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": False}

# HomeAssistant-WhiteAmbiance is a Hue White Ambience
light_types["HomeAssistant-WhiteAmbiance"] = {"type": "Color temperature light", "swversion": "5.130.1.30000", "manufacturername": "Signify Netherlands B.V.", "modelid" : "LTW001", "productname": "Hue ambiance lamp"}
light_types["HomeAssistant-WhiteAmbiance"]["config"] = {"archetype": "sultanbulb", "function": "functional", "direction": "omnidirectional"}
light_types["HomeAssistant-WhiteAmbiance"]["capabilities"] = {"certified": True, "control": {"mindimlevel": 1000,"maxlumen": 806,"ct": {"min": 153,"max": 454}}, "streaming": {"renderer": False,"proxy": False}}
light_types["HomeAssistant-WhiteAmbiance"]["state"] = {"on": False, "bri": 0, "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": False}

# HomeAssistant-Dimmable is a Hue White
light_types["HomeAssistant-Dimmable"] = {"type": "Dimmable light", "swversion": "5.130.1.30000", "manufacturername": "Signify Netherlands B.V.", "modelid" : "LWB006", "productname": "Hue white lamp"}
light_types["HomeAssistant-Dimmable"]["config"] = {"archetype": "classicbulb", "function": "functional", "direction": "omnidirectional"}
light_types["HomeAssistant-Dimmable"]["capabilities"] = {"certified": True, "control": { "maxlumen": 800, "mindimlevel": 2000}, "streaming": { "proxy": False, "renderer": False }}
light_types["HomeAssistant-Dimmable"]["state"] = {"on": False, "bri": 0, "alert": "none", "mode": "homeautomation", "reachable": False}

# HomeAssistant-Switch is a Hue plug in unit
light_types["HomeAssistant-Switch"] = {"type": "On/Off plug-in unit", "swversion": "1.65.9_hB3217DF", "manufacturername": "Signify Netherlands B.V.", "modelid" : "LOM001", "productname": "Hue Smart plug", "productid": "SmartPlug_OnOff_v01-00_01"}
light_types["HomeAssistant-Switch"]["config"] = {"archetype": "plug", "function": "functional", "direction": "omnidirectional"}
light_types["HomeAssistant-Switch"]["capabilities"] = {"certified": True, "control": {}, "streaming": { "renderer": False, "proxy": False }}
light_types["HomeAssistant-Switch"]["state"] = {"on": False, "alert": "none", "mode": "homeautomation", "reachable": False}



