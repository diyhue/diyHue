import requests

import configManager

bridge_config = configManager.bridgeConfig.json_config


def updateLight(light, filename):
    firmware = requests.get('https://github.com/diyhue/Lights/raw/master/Arduino/bin/' + filename, allow_redirects=True)
    open('/tmp/' + filename, 'wb').write(firmware.content)
    file = {'update': open('/tmp/' + filename, 'rb')}
    requests.post('http://' + bridge_config["lights_address"][light]["ip"] + '/update', files=file)
