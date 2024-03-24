# Define light defininitions for discovery features and adding device data to config
lightTypes = {}

## Hue White and Color Ambiance A19 800 Lumen
lightTypes["LCA005"] = {"v1_static":{"type":"Extended color light", "swversion":"1.104.2", "swconfigid":"5419E9E3", "productid":"Philips-LCA005-1-A19ECLv7", "manufacturername":"Signify Netherlands B.V."}}
lightTypes["LCA005"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LCA005"]["v1_static"]["capabilities"] = {"certified":True, "control":{"colorgamut":[[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]], "colorgamuttype":"C", "ct":{"max":500, "min":153}, "maxlumen":800, "mindimlevel":1000}, "streaming":{"proxy":False, "renderer":True}}
lightTypes["LCA005"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"sultan_bulb", "product_name":"Hue color lamp", "software_version":"1.104.2"}
lightTypes["LCA005"]["state"] = {"on":False, "bri":200, "hue":0, "sat":0, "xy":[0.0, 0.0], "ct":461, "alert":"none", "mode":"homeautomation", "effect":"none", "colormode":"ct", "reachable":True}
lightTypes["LCA005"]["config"] = {"archetype":"sultanbulb", "function":"mixed", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":True}}
lightTypes["LCA005"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue Color Bulb #1
lightTypes["LCT001"] = {"v1_static":{"type":"Extended color light", "manufacturername":"Signify Netherlands B.V.", "swversion":"1.104.2"}}
lightTypes["LCT001"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LCT001"]["v1_static"]["capabilities"] = {"certified":True, "control":{"colorgamut":[[0.675,0.322],[0.409,0.518],[0.167,0.04]], "colorgamuttype":"B", "ct":{"max":500, "min":153}, "maxlumen":600, "mindimlevel":5000}, "streaming":{"proxy":False, "renderer":True}}
lightTypes["LCT001"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"sultan_bulb", "product_name":"Hue color lamp", "software_version":"1.104.2"}
lightTypes["LCT001"]["state"] = {"alert":"none", "bri":0, "colormode":"xy", "effect":"none", "hue":0, "mode":"homeautomation", "on":False, "reachable":True, "sat":0, "xy":[0.408,0.517]}
lightTypes["LCT001"]["config"] = {"archetype":"sultanbulb", "direction":"omnidirectional", "function":"mixed", "startup":{"configured":True, "mode":"safety"}}
lightTypes["LCT001"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue Color Bulb #2
lightTypes["LCT015"] = {"v1_static":{"type":"Extended color light", "swversion":"1.104.2", "swconfigid":"772B0E5E", "productid":"Philips-LCT015-1-A19ECLv5", "manufacturername":"Signify Netherlands B.V."}}
lightTypes["LCT015"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LCT015"]["v1_static"]["capabilities"] = {"certified":True, "control":{"colorgamut":[[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]], "colorgamuttype":"C", "ct":{"max":500, "min":153}, "maxlumen":800, "mindimlevel":1000}, "streaming":{"proxy":False, "renderer":True}}
lightTypes["LCT015"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"sultan_bulb", "product_name":"Hue color lamp", "software_version":"1.104.2"}
lightTypes["LCT015"]["state"] = {"on":False, "bri":200, "hue":0, "sat":0, "xy":[0.0, 0.0], "ct":461, "alert":"none", "mode":"homeautomation", "effect":"none", "colormode":"ct", "reachable":True}
lightTypes["LCT015"]["config"] = {"archetype":"sultanbulb", "function":"mixed", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":True}}
lightTypes["LCT015"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue White and Color Ambiance GU10 w/BT
lightTypes["LCG002"] = {"v1_static":{"type":"Extended color light", "swversion":"1.104.2", "swconfigid":"D779D146", "productid":"Philips-LCG002-3-GU10ECLv2", "manufacturername":"Signify Netherlands B.V."}}
lightTypes["LCG002"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LCG002"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":200, "maxlumen":300, "colorgamuttype":"C", "colorgamut":[[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]], "ct":{"min":153, "max":500}}, "streaming":{"renderer":True, "proxy":True}}
lightTypes["LCG002"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"spot_bulb", "product_name":"Hue White and Color Ambiance GU10 w/ BT", "software_version":"1.104.2"}
lightTypes["LCG002"]["state"] = {"on":False, "bri":200, "hue":0, "sat":0, "xy":[0.0, 0.0], "ct":461, "alert":"none", "mode":"homeautomation", "effect":"none", "colormode":"xy", "reachable":True}
lightTypes["LCG002"]["config"] = {"archetype":"spotbulb", "function":"mixed", "direction":"downwards", "startup":{"mode":"safety", "configured":True}}
lightTypes["LCG002"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue Lightstrip Plus
lightTypes["LST002"] = {"v1_static":{"type":"Color light", "manufacturername":"Signify Netherlands B.V.", "swversion":"1.104.2", "productname":"Hue lightstrip plus", "swconfigid":"59F2C3A3", "productid":"Philips-LST002-1-LedStripsv3"}}
lightTypes["LST002"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LST002"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":40, "maxlumen":1600, "colorgamuttype":"C", "colorgamut":[[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]], "ct":{"min":153, "max":500}}, "streaming":{"renderer":True, "proxy":True}}
lightTypes["LST002"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"hue_lightstrip", "product_name":"Hue lightstrip plus", "software_version":"1.104.2"}
lightTypes["LST002"]["state"] = {"on":False, "bri":200, "hue":0, "sat":0, "xy":[0.0, 0.0], "ct":461, "alert":"none", "mode":"homeautomation", "effect":"none", "colormode":"ct", "reachable":True}
lightTypes["LST002"]["config"] = {"archetype":"huelightstrip",	"function":"mixed", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":False}}
lightTypes["LST002"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue White Ambiance GU10 w/BT
lightTypes["LTG002"] = {"v1_static":{"type":"Color temperature light", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue Runner spot", "swversion":"1.104.2", "swconfigid":"87D6EF03", "productid":"Philips-LTG002-3-GU10CTv2"}}
lightTypes["LTG002"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LTG002"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":200, "maxlumen":350, "ct":{"min":153, "max":454}}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LTG002"]["config"] = {"archetype":"spotbulb", "function":"functional", "direction":"downwards", "startup":{"mode":"safety", "configured":True}}
lightTypes["LTG002"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LTG002", "product_archetype":"spot_bulb", "product_name":"Hue White Ambiance GU10 w/BT", "software_version":"1.104.2"}
lightTypes["LTG002"]["state"] = {"on":False, "colormode":"ct", "alert":"select", "mode":"homeautomation", "reachable":True, "bri":127, "ct":369}
lightTypes["LTG002"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Dimmable Hue Bulb
lightTypes["LWB010"] = {"v1_static":{"type":"Dimmable light", "manufacturername":"Signify Netherlands B.V.", "swversion":"1.50.2_r30933", "swconfigid":"322BB2EC", "productid":"Philips-LWB010-1-A19DLv4"}}
lightTypes["LWB010"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LWB010"]["config"] = {"archetype":"classicbulb", "function":"mixed", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":True}}
lightTypes["LWB010"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":5000, "maxlumen":806}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LWB010"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"classic_bulb", "product_name":"Hue White B22", "software_version":"1.104.2"}
lightTypes["LWB010"]["state"] = {"on":False, "bri":254, "alert":"none", "mode":"homeautomation", "reachable":True}
lightTypes["LWB010"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue White GU10
lightTypes["LWG001"] = {"v1_static":{"type":"Dimmable light", "manufacturername":"Signify Netherlands B.V.", "swversion":"1.46.13_r26312", "swconfigid":"ACCF4E76", "productid":"Philips-LWG001-1-GU10DLv1"}}
lightTypes["LWG001"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LWG001"]["config"] = {"archetype":"spotbulb", "function":"mixed", "direction":"downwards", "startup":{"mode":"safety", "configured":True}}
lightTypes["LWG001"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":5000, "maxlumen":400}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LWG001"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"spot_bulb", "product_name":"Hue white spot", "software_version":"1.46.13_r26312"}
lightTypes["LWG001"]["state"] = {"on":False, "bri":254, "alert":"none", "mode":"homeautomation", "reachable":True}
lightTypes["LWG001"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Control Temp Hue Bulb
lightTypes["LTW001"] = {"v1_static":{"type":"Color temperature light", "manufacturername":"Signify Netherlands B.V.", "swversion":"1.104.2"}}
lightTypes["LTW001"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LTW001"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":1000, "maxlumen":806, "ct":{"min":153, "max":454}}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LTW001"]["config"] = {"archetype":"classicbulb", "function":"functional", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":True}}
lightTypes["LTW001"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "product_archetype":"classic_bulb", "product_name":"Dimmable light", "software_version":"1.76.6"}
lightTypes["LTW001"]["state"] = {"on":False, "colormode":"ct", "alert":"none", "mode":"homeautomation", "reachable":True, "bri":254, "ct":230}
lightTypes["LTW001"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue White Ambiance GU10
lightTypes["LTW013"] = {"v1_static":{"type":"Color temperature light", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue Ambiance spot", "swversion":"1.108.7", "swconfigid":"116B9B72", "productid":"Philips-LTW013-1-GU10CTv1"}}
lightTypes["LTW013"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LTW013"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":1000, "maxlumen":350, "ct":{"min":153, "max":454}}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LTW013"]["config"] = {"archetype":"spotbulb", "function":"functional", "direction":"downwards", "startup":{"mode":"safety", "configured":True}}
lightTypes["LTW013"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LTW013", "product_archetype":"spot_bulb", "product_name":"Hue White Ambiance GU10", "software_version":"1.108.7"}
lightTypes["LTW013"]["state"] = {"on":False, "colormode":"ct", "alert":"select", "mode":"homeautomation", "reachable":True, "bri":127, "ct":369}
lightTypes["LTW013"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}
lightTypes["LTW014"] = lightTypes["LTW013"]

## Hue Gradient TV Lightstrip
lightTypes["LCX002"] = {"v1_static":{"type":"Extended color light", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue play gradient lightstrip", "swversion":"1.104.2", "swconfigid":"C74E5108", "productid":"Philips-LCX002-1-LedStripPXv1"}}
lightTypes["LCX002"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-11-02T19:46:12"}
lightTypes["LCX002"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":100, "maxlumen":1600, "colorgamuttype":"C", "colorgamut":[[0.6915,0.3083],[0.1700,0.7000],[0.1532,0.0475]], "ct":{"min":153, "max":500}}, "streaming":{"renderer":True, "proxy":True}}
lightTypes["LCX002"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LCX002", "product_archetype":"hue_lightstrip_tv", "product_name":"Hue play gradient lightstrip", "software_version":"1.104.2"}
lightTypes["LCX002"]["state"] = {"on":False, "bri":254, "hue":8417, "sat":140, "effect":"none", "xy":[0.0,0.0], "ct":366, "alert":"select", "colormode":"ct", "mode":"homeautomation", "reachable":True, "gradient":{"points":[]}}
lightTypes["LCX002"]["config"] = {"archetype":"huelightstriptv", "function":"mixed", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":False}}
lightTypes["LCX002"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue Signe Gradient
lightTypes["915005987201"] = {"v1_static":{"type":"Extended color light", "manufacturername":"Signify Netherlands B.V.", "productname":"Signe gradient floor", "swversion":"1.94.2", "swconfigid":"DC0A18AF", "productid":"4422-9482-0441_HG01_PSU03"}}
lightTypes["915005987201"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2022-01-13T22:54:51"}
lightTypes["915005987201"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":100, "maxlumen":1600, "colorgamuttype":"C", "colorgamut":[[0.6915,0.3083],[0.1700,0.7000],[0.1532,0.0475]], "ct":{"min":153, "max":500}}, "streaming":{"renderer":True, "proxy":True}}
lightTypes["915005987201"]["device"] = {"certified":True, "hardware_platform_type":"100b-118", "manufacturer_name":"Signify Netherlands B.V.", "model_id":"915005987201", "product_archetype":"hue_signe", "product_name":"Signe gradient floor", "software_version":"1.94.2"}
lightTypes["915005987201"]["state"] = {"on":False, "bri":254, "hue":8417, "sat":140, "effect":"none", "xy":[0.0,0.0], "ct":366, "alert":"select", "colormode":"ct", "mode":"homeautomation", "reachable":True, "gradient":{"points":[]}}
lightTypes["915005987201"]["config"] = {"archetype":"huesigne", "function":"decorative", "direction":"horizontal", "startup":{"mode":"safety", "configured":False}}
lightTypes["915005987201"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue Gradient Lightstrip
lightTypes["LCX004"] = {"v1_static":{"type":"Extended color light", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue gradient lightstrip", "swversion":"1.94.2", "swconfigid":"DC0A18AF", "productid":"4422-9482-0441_HG01_PSU03"}}
lightTypes["LCX004"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2022-01-13T22:54:51"}
lightTypes["LCX004"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":100, "maxlumen":1600, "colorgamuttype":"C", "colorgamut":[[0.6915,0.3083],[0.1700,0.7000],[0.1532,0.0475]], "ct":{"min":153, "max":500}}, "streaming":{"renderer":True, "proxy":True}}
lightTypes["LCX004"]["device"] = {"certified":True, "hardware_platform_type":"100b-118", "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LCX004", "product_archetype":"hue_lightstrip", "product_name":"Hue gradient lightstrip", "software_version":"1.94.2"}
lightTypes["LCX004"]["state"] = {"on":False, "bri":254, "hue":8417, "sat":140, "effect":"none", "xy":[0.0,0.0], "ct":366, "alert":"select", "colormode":"ct", "mode":"homeautomation", "reachable":True, "gradient":{"points":[]}}
lightTypes["LCX004"]["config"] = {"archetype":"huelightstrip", "function":"mixed", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":False}}
lightTypes["LCX004"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue Play Lightstrip
lightTypes["LCX006"] = {"v1_static":{"type":"Extended color light", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue gradient lightstrip", "swversion":"1.94.2", "swconfigid":"DC0A18AF", "productid":"4422-9482-0441_HG01_PSU03"}}
lightTypes["LCX006"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2022-01-13T22:54:51"}
lightTypes["LCX006"]["v1_static"]["capabilities"] = {"certified":True, "control":{"mindimlevel":100, "maxlumen":1600, "colorgamuttype":"C", "colorgamut":[[0.6915,0.3083],[0.1700,0.7000],[0.1532,0.0475]], "ct":{"min":153, "max":500}}, "streaming":{"renderer":True, "proxy":True}}
lightTypes["LCX006"]["device"] = {"certified":True, "hardware_platform_type":"100b-118", "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LCX006", "product_archetype":"hue_lightstrip", "product_name":"Hue gradient lightstrip", "software_version":"1.94.2"}
lightTypes["LCX006"]["state"] = {"on":False, "bri":254, "hue":8417, "sat":140, "effect":"none", "xy":[0.0,0.0], "ct":366, "alert":"select", "colormode":"ct", "mode":"homeautomation", "reachable":True, "gradient":{"points":[]}}
lightTypes["LCX006"]["config"] = {"archetype":"huelightstrip", "function":"mixed", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":False}}
lightTypes["LCX006"]["dynamics"] = {"speed":0, "speed_valid":False, "status":"none", "status_values":["none", "dynamic_palette"]}

## Hue Plug
lightTypes["LOM001"] = {"v1_static":{"type":"On/Off plug-in unit", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue Smart plug", "swversion":"1.104.2", "swconfigid":"A641B5AB", "productid":"SmartPlug_OnOff_v01-00_01"}}
lightTypes["LOM001"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LOM001"]["v1_static"]["capabilities"] = {"certified":True, "control":{}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LOM001"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LOM001", "product_archetype":"plug", "product_name":"Hue Smart plug", "software_version":"1.104.2"}
lightTypes["LOM001"]["state"] = {"on":False, "alert":"select", "mode":"homeautomation", "reachable":True}
lightTypes["LOM001"]["config"] = {"archetype":"plug", "function":"functional", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":True}}
lightTypes["LOM001"]["dynamics"] = {"status":"none", "status_values":["none"]}

lightTypes["LOM004"] = {"v1_static":{"type":"On/Off plug-in unit", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue Smart plug", "swversion":"1.104.2", "swconfigid":"A641B5AB", "productid":"SmartPlug_OnOff_v01-00_01"}}
lightTypes["LOM004"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LOM004"]["v1_static"]["capabilities"] = {"certified":True, "control":{}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LOM004"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LOM001", "product_archetype":"plug", "product_name":"Hue Smart plug", "software_version":"1.104.2"}
lightTypes["LOM004"]["state"] = {"on":False, "alert":"select", "mode":"homeautomation", "reachable":True}
lightTypes["LOM004"]["config"] = {"archetype":"plug", "function":"functional", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":True}}
lightTypes["LOM004"]["dynamics"] = {"status":"none", "status_values":["none"]}

lightTypes["LOM010"] = {"v1_static":{"type":"On/Off plug-in unit", "manufacturername":"Signify Netherlands B.V.", "productname":"Hue Smart plug", "swversion":"1.104.2", "swconfigid":"A641B5AB", "productid":"SmartPlug_OnOff_v01-00_01"}}
lightTypes["LOM010"]["v1_static"]["swupdate"] = {"state":"noupdates", "lastinstall":"2020-12-09T19:13:52"}
lightTypes["LOM010"]["v1_static"]["capabilities"] = {"certified":True, "control":{}, "streaming":{"renderer":False, "proxy":False}}
lightTypes["LOM010"]["device"] = {"certified":True, "manufacturer_name":"Signify Netherlands B.V.", "model_id":"LOM001", "product_archetype":"plug", "product_name":"Hue Smart plug", "software_version":"1.104.2"}
lightTypes["LOM010"]["state"] = {"on":False, "alert":"select", "mode":"homeautomation", "reachable":True}
lightTypes["LOM010"]["config"] = {"archetype":"plug", "function":"functional", "direction":"omnidirectional", "startup":{"mode":"safety", "configured":True}}
lightTypes["LOM010"]["dynamics"] = {"status":"none", "status_values":["none"]}

archetype = {"tableshade":"table_shade",
    "flexiblelamp":"flexible_lamp",
    "tablewash":"table_wash",
    "christmastree":"christmas_tree",
    "floorshade":"floor_shade",
    "floorlantern":"floor_lantern",
    "bollard":"bollard",
    "groundspot":"ground_spot",
    "recessedfloor":"recessed_floor",
    "wallwasher":"wall_washer",
    "pendantround":"pendant_round",
    "pendantlong":"pendant_long",
    "ceilinground":"ceiling_round",
    "ceilingsquare":"ceiling_square",
    "singlespot":"single_spot",
    "doublespot":"double_spot",
    "recessedceiling":"recessed_ceiling",
    "walllantern":"wall_lantern",
    "wallshade":"wall_shade",
    "wallspot":"wall_spot",
    "sultanbulb":"sultan_bulb",
    "classicbulb":"classic_bulb",
    "spotbulb":"spot_bulb",
    "floodbulb":"flood_bulb",
    "candlebulb":"candle_bulb",
    "vintagebulb":"vintage_bulb",
    "lusterbulb":"luster_bulb",
    "huelightstrip":"hue_lightstrip",
    "huego":"hue_go",
    "hueplay":"hue_play",
    "huebloom":"hue_bloom",
    "hueiris":"hue_iris",
    "plug":"plug",
    "huecentris":"hue_centris",
    "huelightstriptv":"hue_lightstrip_tv",
    "huesigne":"hue_signe"
}
