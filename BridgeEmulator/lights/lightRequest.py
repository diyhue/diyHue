import logging, json
from functions.request import sendRequest
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness
from lights.protocols import protocols
from datetime import datetime, timedelta
from time import sleep
from lights.manage import updateGroupStats


def syncWithLights(lights, addresses, users, groups, off_if_unreachable): #update Hue Bridge lights states
    while True:
        logging.info("sync with lights")
        for light in addresses:
            protocol_name = addresses[light]["protocol"]
            for protocol in protocols:
                if "protocols." + protocol_name == protocol.__name__:
                    try:
                        light_state = protocol.get_light_state(addresses[light], lights[light])
                        lights[light]["state"].update(light_state)
                        lights[light]["state"]["reachable"] = True
                    except Exception as e:
                        lights[light]["state"]["reachable"] = False
                        lights[light]["state"]["on"] = False
                        logging.warning(lights[light]["name"] + " is unreachable: %s", e)

            if off_if_unreachable:
                if lights[light]["state"]["reachable"] == False:
                    lights[light]["state"]["on"] = False
            updateGroupStats(light, lights, groups)

        sleep(10) #wait at last 10 seconds before next sync
        i = 0
        while i < 300: #sync with lights every 300 seconds or instant if one user is connected
            for user in users.keys():
                lu = users[user]["last use date"]
                try: #in case if last use is not a proper datetime
                    lu = datetime.strptime(lu, "%Y-%m-%dT%H:%M:%S")
                    if abs(datetime.now() - lu) <= timedelta(seconds = 2):
                        i = 300
                        break
                except:
                    pass
            i += 1
            sleep(1)
