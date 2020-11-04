from threading import Thread

import configManager
from protocols import tradfri, yeelight, tasmota, shelly, esphome, mqtt, hyperion, deconz, native

bridge_config = configManager.bridgeConfig.json_config
new_lights = configManager.runtimeConfig.newLights

def scan_for_lights(): #scan for ESP8266 lights and strips
    Thread(target=yeelight.discover, args=[bridge_config, new_lights]).start()
    Thread(target=tasmota.discover, args=[bridge_config, new_lights]).start()
    Thread(target=shelly.discover, args=[bridge_config, new_lights]).start()
    Thread(target=esphome.discover, args=[bridge_config, new_lights]).start()
    Thread(target=mqtt.discover, args=[bridge_config, new_lights]).start()
    Thread(target=hyperion.discover, args=[bridge_config, new_lights]).start()
    Thread(target=deconz.deconz.scanDeconz).start()
    Thread(target=native.discover, args=[bridge_config, new_lights]).start()

    tradfri.discover.scanTradfri()
    configManager.bridgeConfig.save_config()
