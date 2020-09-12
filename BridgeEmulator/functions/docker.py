import os
from subprocess import call
from shutil import copyfile
import requests

def dockerSetup(mac):
    if os.path.isfile("/opt/hue-emulator/export/cert.pem"):
        print("Restoring Certificate")
        copyfile("/opt/hue-emulator/export/cert.pem", "/opt/hue-emulator/cert.pem")
        print("Certificate Restored")
    else:
        print("Generating certificate")
        call(["/opt/hue-emulator/genCert.sh", mac])
        copyfile("/opt/hue-emulator/cert.pem", "/opt/hue-emulator/export/cert.pem")
        print("Certificate created")

    if os.path.isfile("/opt/hue-emulator/export/config.json"):
        print("Restoring config")
        copyfile("/opt/hue-emulator/export/config.json", "/opt/hue-emulator/config.json")
        print("Config restored")
    else:
        print("Downloading default config")
        res = requests.get("https://raw.githubusercontent.com/diyHue/diyHue/master/BridgeEmulator/default-config.json", allow_redirects=True)
        open('/opt/hue-emulator/config.json', 'w+').write(res.text)
        copyfile("/opt/hue-emulator/config.json", "/opt/hue-emulator/export/config.json")
        print("Config downloaded")
