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
        print("Copying default config")
        copyfile("/opt/hue-emulator/default-config.json", "/opt/hue-emulator/export/config.json")
        print("Config copied")
