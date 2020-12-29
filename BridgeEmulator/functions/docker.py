import os
from subprocess import call
from shutil import copyfile
import requests

def dockerSetup(mac, configPath):
    if os.path.isfile(configPath + "/cert.pem"):
        print("SSL certificate found")
    else:
        print("Generating certificate")
        serial = mac[:6] + "fffe" + mac[-6:]
        call(["/opt/hue-emulator/genCert.sh", serial])
        copyfile("/opt/hue-emulator/cert.pem", configPath + "/cert.pem")
        print("Certificate created")

    if os.path.isfile(configPath + "/config.json"):
        print("Config file found")
    else:
        print("Downloading default config")
        res = requests.get("https://raw.githubusercontent.com/diyHue/diyHue/master/BridgeEmulator/default-config.json", allow_redirects=True)
        open(configPath + '/config.json', 'w+').write(res.text)
        print("Config downloaded")
