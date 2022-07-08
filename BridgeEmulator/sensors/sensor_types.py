sensorTypes = {}
sensorTypes["PHDL00"] = {"Daylight": {"state":{"daylight":None,"lastupdated":"none"}, "config":{"on":True,"configured":False,"sunriseoffset":30,"sunsetoffset":-30}, "static": {"manufacturername":"Signify Netherlands B.V.","swversion":"1.0"}}}
sensorTypes["SML001"] = {"ZLLTemperature" : {"state": {"temperature": None,"lastupdated": "none"},"config": {"on": False,"battery": 100,"reachable": True,"alert": "none","ledindication": False,"usertest": False,"pending": []}, "static": {"swupdate": {"state": "noupdates","lastinstall": "2021-03-16T21:16:40"}, "manufacturername": "Signify Netherlands B.V.","productname": "Hue temperature sensor","swversion": "6.1.1.27575","capabilities": {"certified": True,"primary": False}}},
                        "ZLLPresence" : { "state": {"lastupdated": "none","presence": None  }, "config": {"on": False,"battery": 100,"reachable": True,"alert": "none","ledindication": False,"usertest": False,"sensitivity": 2,"sensitivitymax": 2,"pending": []  }, "static": {"swupdate": {"state": "noupdates","lastinstall": "2021-03-16T21:16:40"}, "manufacturername": "Signify Netherlands B.V.", "productname": "Hue motion sensor", "swversion": "6.1.1.27575", "capabilities":{"certified":True,"primary":True}}},
                        "ZLLLightLevel" : {"state": {"dark": True,"daylight": False,"lightlevel": 6000,"lastupdated": "none"}, "config": {"on": False,"battery": 100,"reachable": True,"alert": "none","tholddark": 9346,"tholdoffset": 7000,"ledindication": False,"usertest": False,"pending": []}, "static": {"swupdate": {  "state": "noupdates",  "lastinstall": "2021-03-16T21:16:40"}, "manufacturername": "Signify Netherlands B.V.","productname": "Hue ambient light sensor","swversion": "6.1.1.27575","capabilities": {  "certified": True,  "primary": False}}}}

sensorTypes["RWL021"] = {"ZLLSwitch": {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "static": {"swupdate": {"state": "noupdates", "lastinstall": "2021-03-11T12:38:37"}, "manufacturername": "Signify Netherlands B.V.", "swversion": "6.1.1.28573", "diversityid": "73bbabea-3420-499a-9856-46bf437e119b", "productname": "Hue dimmer switch", "capabilities": {"certified": True,"primary": True,"inputs": [{"repeatintervals": [800],"events": [{"buttonevent": 1000,"eventtype": "initial_press"}, {"buttonevent": 1001,"eventtype": "repeat"}, {"buttonevent": 1002,"eventtype": "short_release"}, {"buttonevent": 1003,"eventtype": "long_release"}]}, {"repeatintervals": [800],"events": [{"buttonevent": 2000,"eventtype": "initial_press"}, {"buttonevent": 2001,"eventtype": "repeat"}, {"buttonevent": 2002,"eventtype": "short_release"}, {"buttonevent": 2003,"eventtype": "long_release"}]}, {"repeatintervals": [800],"events": [{"buttonevent": 3000,"eventtype": "initial_press"}, {"buttonevent": 3001,"eventtype": "repeat"}, {"buttonevent": 3002,"eventtype": "short_release"}, {"buttonevent": 3003,"eventtype": "long_release"}]}, {"repeatintervals": [800],"events": [{"buttonevent": 4000,"eventtype": "initial_press"}, {"buttonevent": 4001,"eventtype": "repeat"}, {"buttonevent": 4002,"eventtype": "short_release"}, {"buttonevent": 4003,"eventtype": "long_release"}]}]}}}}
sensorTypes["ZGPSWITCH"] = {"ZGPSwitch": {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "static": {"manufacturername": "Signify Netherlands B.V.", "swversion": ""}}}
sensorTypes["RWL022"] = sensorTypes["RWL021"]
sensorTypes["RWL022"]["ZHASwitch"] = sensorTypes["RWL022"]["ZLLSwitch"]
sensorTypes["TRADFRI remote control"] = {"ZHASwitch": {"state": {"buttonevent": 1002, "lastupdated": "none"}, "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "static": {"swversion": "1.2.214", "manufacturername": "IKEA of Sweden"}}}
sensorTypes["TRADFRI on/off switch"] = {"ZHASwitch": {"state": {"buttonevent": 1002, "lastupdated": "none"}, "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "static": {"swversion": "2.2.008", "manufacturername": "IKEA of Sweden"}}}
sensorTypes["TRADFRI wireless dimmer"] = {"ZHASwitch": {"state": {"buttonevent": 1002, "lastupdated": "none"}, "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "static": {"swversion": "1.2.248", "manufacturername": "IKEA of Sweden"}}}
sensorTypes["GreenPower_2"] = {"ZHASwitch": {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "static": {"manufacturername": "Signify Netherlands B.V.", "swversion": ""}}}
#sensorTypes["GreenPower_2"] = {"FOHSwitch": {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "static": {"manufacturername": "Signify Netherlands B.V.", "swversion": ""}}}




# {
#     "state": {
#         "buttonevent": 21,
#         "lastupdated": "2022-06-27T13:55:33"
#     },
#     "swupdate": {
#         "state": "notupdatable",
#         "lastinstall": null
#     },
#     "config": {
#         "on": true
#     },
#     "name": "Friends of Hue Switch 1",
#     "type": "ZGPSwitch",
#     "modelid": "FOHSWITCH",
#     "manufacturername": "PhilipsFoH",
#     "productname": "Friends of Hue Switch",
#     "diversityid": "ded6468f-6b26-4a75-9582-f2b52d36a5a3",
#     "uniqueid": "00:00:00:00:01:70:10:9f-f2",
#     "capabilities": {
#         "certified": true,
#         "primary": true,
#         "inputs": [
#             {
#                 "repeatintervals": [],
#                 "events": [
#                     {
#                         "buttonevent": 16, #Top Left
#                         "eventtype": "initial_press"
#                     },
#                     {
#                         "buttonevent": 20,
#                         "eventtype": "short_release"
#                     }
#                 ]
#             },
#             {
#                 "repeatintervals": [],
#                 "events": [
#                     {
#                         "buttonevent": 17, #Bottom Left
#                         "eventtype": "initial_press"
#                     },
#                     {
#                         "buttonevent": 21,
#                         "eventtype": "short_release"
#                     }
#                 ]
#             },
#             {
#                 "repeatintervals": [],
#                 "events": [
#                     {
#                         "buttonevent": 19, #Top Right
#                         "eventtype": "initial_press"
#                     },
#                     {
#                         "buttonevent": 23,
#                         "eventtype": "short_release"
#                     }
#                 ]
#             },
#             {
#                 "repeatintervals": [],
#                 "events": [
#                     {
#                         "buttonevent": 18, #Bottom Right
#                         "eventtype": "initial_press"
#                     },
#                     {
#                         "buttonevent": 22,
#                         "eventtype": "short_release"
#                     }
#                 ]
#             }
#         ]
#     }
# }

