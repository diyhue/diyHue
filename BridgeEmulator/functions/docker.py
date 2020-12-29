import os
from subprocess import call
from shutil import copyfile
import requests

def dockerSetup(mac, configPath):
    if not os.path.exists(configPath + "/export"):
        os.makedirs(configPath + "/export")
    if os.path.isfile(configPath + "/export/cert.pem"):
        print("Restoring Certificate")
        copyfile(configPath + "/export/cert.pem", configPath + "/cert.pem")
        print("Certificate Restored")
    else:
        print("Generating certificate")
        serial = mac[:6] + "fffe" + mac[-6:]
        call(["/opt/hue-emulator/genCert.sh", serial])
        copyfile("/opt/hue-emulator/cert.pem", configPath + "/cert.pem")
        copyfile("/opt/hue-emulator/cert.pem", configPath + "/export/cert.pem")
        print("Certificate created")

    if os.path.isfile(configPath + "/export/config.json"):
        print("Restoring config")
        copyfile(configPath + "/export/config.json", configPath + "/config.json")
        print("Config restored")
    else:
        print("Downloading default config")
        res = requests.get("https://raw.githubusercontent.com/diyHue/diyHue/master/BridgeEmulator/default-config.json", allow_redirects=True)
        open(configPath + '/config.json', 'w+').write(res.text)
        copyfile(configPath + "/config.json", configPath + "/export/config.json")
        print("Config downloaded")
