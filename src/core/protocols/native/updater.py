import requests

import configManager

bridge_config = configManager.bridgeConfig.json_config


def updateLight(light, filename):
    firmware = requests.get('https://github.com/diyhue/Lights/raw/master/Arduino/bin/' + filename, allow_redirects=True)
    open('/tmp/' + filename, 'wb').write(firmware.content)
    file = {'update': open('/tmp/' + filename, 'rb')}
    requests.post('http://' + bridge_config["lights_address"][light]["ip"] + '/update', files=file)


def getLightsVersions():
    lights = {}
    githubCatalog = json.loads(requests.get('https://raw.githubusercontent.com/diyhue/Lights/master/catalog.json').text)
    for light in bridge_config["lights_address"].keys():
        if bridge_config["lights_address"][light]["protocol"] in ["native_single", "native_multi"]:
            if "light_nr" not in bridge_config["lights_address"][light] or bridge_config["lights_address"][light][
                "light_nr"] == 1:
                currentData = json.loads(
                    requests.get('http://' + bridge_config["lights_address"][light]["ip"] + '/detect', timeout=3).text)
                lights[light] = {"name": currentData["name"], "currentVersion": currentData["version"],
                                 "lastVersion": githubCatalog[currentData["type"]]["version"],
                                 "firmware": githubCatalog[currentData["type"]]["filename"]}
    return lights
