# Define light defininitions for discovery features and adding device data to config
lightTypes = {}

lightTypes["LCT001"] = {"v1_static": {"type":"Extended color light", "manufacturername": "Signify Netherlands B.V.", "swversion": "1.46.13_r26312"}}
lightTypes["LCT001"]["v1_static"]["swupdate"] = {"state": "noupdates","lastinstall": "2020-12-09T19:13:52"}
lightTypes["LCT001"]["v1_static"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.675,0.322],[0.409,0.518],[0.167,0.04]],"colorgamuttype": "B","ct": {"max": 500,"min": 153},"maxlumen": 600,"mindimlevel": 5000},"streaming": {"proxy": False,"renderer": True}}
lightTypes["LCT001"]["state"] = {"alert": "none", "bri":0, "colormode": "xy", "effect": "none","hue": 0, "mode": "homeautomation","on": False,"reachable": True, "sat": 0,"xy": [0.408,0.517]}
lightTypes["LCT001"]["config"] = {"archetype": "sultanbulb","direction": "omnidirectional","function": "mixed","startup": {"configured": True, "mode": "powerfail"}}

lightTypes["LCT015"] = {"v1_static": {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}}
lightTypes["LCT015"]["v1_static"]["swupdate"] = {"state": "noupdates","lastinstall": "2020-12-09T19:13:52"}
lightTypes["LCT015"]["v1_static"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]],"colorgamuttype": "C","ct": {"max": 500,"min": 153},"maxlumen": 800,"mindimlevel": 1000},"streaming": {"proxy": False,"renderer": True}}
lightTypes["LCT015"]["v2_static"] = {"product_data": {"certified": True,"manufacturer_name": "Signify Netherlands B.V.","model_id": "LCT015","product_archetype": "sultan_bulb","product_name": "Hue color lamp","software_version": "1.50.2"}}
lightTypes["LCT015"]["v2_static"]["metadata"] = {"archetype": "sultan_bulb"}
lightTypes["LCT015"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
lightTypes["LCT015"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}

lightTypes["LST002"] = {"v1_static": {"type": "Color light", "swversion": "5.127.1.26581"}}
lightTypes["LST002"]["v1_static"]["swupdate"] = {"state": "noupdates","lastinstall": "2020-12-09T19:13:52"}
lightTypes["LST002"]["v1_static"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.704,0.296],[0.2151,0.7106],[0.138,0.08]],"colorgamuttype": "A","maxlumen": 200,"mindimlevel": 10000},"streaming": {"proxy": False,"renderer": True}}
lightTypes["LST002"]["v2_static"] = {"metadata": {"archetype": "hue_lightstrip"}}
lightTypes["LST002"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
lightTypes["LST002"]["config"] = {"archetype": "huelightstrip",	"function": "mixed", "direction": "omnidirectional", "startup": {"mode": "powerfail", "configured": False}}

lightTypes["LWB010"] = {"v1_static": {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "Philips", "productid": "Philips-LWB010-1-A19DLv4"}}
lightTypes["LWB010"]["v1_static"]["swupdate"] = {"state": "noupdates","lastinstall": "2020-12-09T19:13:52"}
lightTypes["LWB010"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}
lightTypes["LWB010"]["v1_static"]["capabilities"] = {"certified": True,"control": {"mindimlevel": 5000, "maxlumen": 806}, "streaming": {"renderer": False, "proxy": False}}
lightTypes["LWB010"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}

lightTypes["LTW001"] = {"v1_static": {"type": "Color temperature light", "swversion": "1.46.13_r26312"}}
lightTypes["LTW001"]["v1_static"]["swupdate"] = {"state": "noupdates","lastinstall": "2020-12-09T19:13:52"}
lightTypes["LTW001"]["v1_static"]["capabilities"] = {"certified": True,"control": {"mindimlevel": 1000,"maxlumen": 806,"ct": {"min": 153,"max": 454}},"streaming": {"renderer": False,"proxy": False}}
lightTypes["LTW001"]["config"] = {"archetype": "classicbulb","function": "functional","direction": "omnidirectional"}
lightTypes["LTW001"]["state"] = {"on": False, "colormode": "ct", "alert": "none", "mode": "homeautomation", "reachable": True, "bri": 254, "ct": 230}

lightTypes["LCX002"] = {"v1_static": {"type": "Extended color light", "manufacturername": "Signify Netherlands B.V.", "productname": "Hue play gradient lightstrip","swversion": "1.72.4_h5293B5","swconfigid": "C74E5108","productid": "Philips-LCX002-1-LedStripPXv1"}}
lightTypes["LCX002"]["v1_static"]["swupdate"] = {"state": "noupdates","lastinstall": "2020-11-02T19:46:12"}
lightTypes["LCX002"]["v1_static"]["capabilities"] = {"certified": True,"control": {"mindimlevel": 100,"maxlumen": 1600,"colorgamuttype": "C","colorgamut": [[0.6915,0.3083],[0.1700,0.7000],[0.1532,0.0475]],"ct": {"min": 153,"max": 500}},"streaming": {"renderer": True,"proxy": True}}
lightTypes["LCX002"]["v2_static"] = {"product_data": {"certified": True,"manufacturer_name": "Signify Netherlands B.V.","model_id": "LCX002","product_archetype": "hue_lightstrip_tv","product_name": "Hue play gradient lightstrip","software_version": "1.72.4"}}
lightTypes["LCX002"]["v2_static"]["metadata"] = {"archetype": "hue_lightstrip_tv"}
lightTypes["LCX002"]["state"] = {"on": False, "bri": 254,"hue": 8417,"sat": 140,"effect": "none","xy": [0.0,0.0],"ct": 366,"alert": "select","colormode": "ct","mode": "homeautomation","reachable": True}
lightTypes["LCX002"]["config"] = {"archetype": "huelightstriptv","function": "mixed","direction": "omnidirectional","startup": {"mode": "powerfail","configured": False}}

lightTypes["LOM001"] = {"v1_static": {"type": "On/Off plug-in unit","manufacturername": "Signify Netherlands B.V.","productname": "Hue Smart plug","swversion": "1.65.9_hB3217DF","swconfigid": "A641B5AB","productid": "SmartPlug_OnOff_v01-00_01"}}
lightTypes["LOM001"]["v1_static"]["swupdate"] = {"state": "noupdates","lastinstall": "2020-12-09T19:13:52"}
lightTypes["LOM001"]["v1_static"]["capabilities"] = {"certified": True,"control": {},"streaming": {"renderer": False,"proxy": False}}
lightTypes["LOM001"]["v2_static"] = {"product_data": {"certified": True,"manufacturer_name": "Signify Netherlands B.V.","model_id": "LOM001","product_archetype": "plug","product_name": "Hue Smart plug","software_version": "1.76.10"}}
lightTypes["LOM001"]["v2_static"]["metadata"] = {"archetype": "plug"}
lightTypes["LOM001"]["state"] = {"on": False,"alert": "select","mode": "homeautomation","reachable": True}
lightTypes["LOM001"]["config"] = {"archetype": "plug","function": "functional","direction": "omnidirectional","startup":{"mode": "safety","configured": True}}
