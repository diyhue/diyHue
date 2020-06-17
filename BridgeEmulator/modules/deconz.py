import logging
import Globals

def scanDeconz():
    if not Globals.bridge_config["deconz"]["enabled"]:
        if "username" not in Globals.bridge_config["deconz"]:
            try:
                registration = json.loads(sendRequest("http://" + deconz_ip + ":" + str(Globals.bridge_config["deconz"]["port"]) + "/api", "POST", "{\"username\": \"283145a4e198cc6535\", \"devicetype\":\"Hue Emulator\"}"))
            except:
                logging.info("registration fail, is the link button pressed?")
                return
            if "success" in registration[0]:
                Globals.bridge_config["deconz"]["username"] = registration[0]["success"]["username"]
                Globals.bridge_config["deconz"]["enabled"] = True
    if "username" in Globals.bridge_config["deconz"]:
        deconz_config = json.loads(sendRequest("http://" + deconz_ip + ":" + str(Globals.bridge_config["deconz"]["port"]) + "/api/" + Globals.bridge_config["deconz"]["username"] + "/config", "GET", "{}"))
        Globals.bridge_config["deconz"]["websocketport"] = deconz_config["websocketport"]

        #lights
        deconz_lights = json.loads(sendRequest("http://" + deconz_ip + ":" + str(Globals.bridge_config["deconz"]["port"]) + "/api/" + Globals.bridge_config["deconz"]["username"] + "/lights", "GET", "{}"))
        for light in deconz_lights:
            if light not in Globals.bridge_config["deconz"]["lights"] and "modelid" in deconz_lights[light]:
                new_light_id = nextFreeId(bridge_config, "lights")
                logging.info("register new light " + new_light_id)
                Globals.bridge_config["lights"][new_light_id] = deconz_lights[light]
                Globals.bridge_config["lights_address"][new_light_id] = {"username": Globals.bridge_config["deconz"]["username"], "light_id": light, "ip": deconz_ip + ":" + str(Globals.bridge_config["deconz"]["port"]), "protocol": "deconz"}
                Globals.bridge_config["deconz"]["lights"][light] = {"bridgeid": new_light_id, "modelid": deconz_lights[light]["modelid"], "type": deconz_lights[light]["type"]}

        #sensors
        deconz_sensors = json.loads(sendRequest("http://" + deconz_ip + ":" + str(Globals.bridge_config["deconz"]["port"]) + "/api/" + Globals.bridge_config["deconz"]["username"] + "/sensors", "GET", "{}"))
        for sensor in deconz_sensors:
            if sensor not in Globals.bridge_config["deconz"]["sensors"] and "modelid" in deconz_sensors[sensor]:
                new_sensor_id = nextFreeId(bridge_config, "sensors")
                if deconz_sensors[sensor]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
                    logging.info("register new " + deconz_sensors[sensor]["modelid"])
                    Globals.bridge_config["sensors"][new_sensor_id] = {"config": deconz_sensors[sensor]["config"], "manufacturername": deconz_sensors[sensor]["manufacturername"], "modelid": deconz_sensors[sensor]["modelid"], "name": deconz_sensors[sensor]["name"], "state": deconz_sensors[sensor]["state"], "type": deconz_sensors[sensor]["type"], "uniqueid": deconz_sensors[sensor]["uniqueid"]}
                    if "swversion" in  deconz_sensors[sensor]:
                        Globals.bridge_config["sensors"][new_sensor_id]["swversion"] = deconz_sensors[sensor]["swversion"]
                    Globals.bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "TRADFRI motion sensor":
                    logging.info("register TRADFRI motion sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    Globals.bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "internal"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.vibration.aq1":
                    logging.info("register Xiaomi Vibration sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    Globals.bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "astral"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion.aq2":
                    if deconz_sensors[sensor]["type"] == "ZHALightLevel":
                        logging.info("register new Xiaomi light sensor")
                        Globals.bridge_config["sensors"][new_sensor_id] = {"name": "Hue ambient light sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        Globals.bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:-1] + "2", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        Globals.bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                    elif deconz_sensors[sensor]["type"] == "ZHAPresence":
                        logging.info("register new Xiaomi motion sensor")
                        Globals.bridge_config["sensors"][new_sensor_id] = {"name": deconz_sensors[sensor]["name"], "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
                        Globals.bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion":
                    logging.info("register Xiaomi Motion sensor w/o light sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    Globals.bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                else:
                    Globals.bridge_config["sensors"][new_sensor_id] = deconz_sensors[sensor]
                    Globals.bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}

            else: #temporary patch for config compatibility with new release
                Globals.bridge_config["deconz"]["sensors"][sensor]["modelid"] = deconz_sensors[sensor]["modelid"]
                Globals.bridge_config["deconz"]["sensors"][sensor]["type"] = deconz_sensors[sensor]["type"]
        generateDxState()

        if "websocketport" in Globals.bridge_config["deconz"]:
            logging.info("Starting deconz websocket")
            Thread(target=websocketClient).start()
