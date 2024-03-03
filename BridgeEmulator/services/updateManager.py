import requests
import configManager
import logManager
import json
from datetime import datetime, timezone
import subprocess

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)

def versionCheck():
    swversion = bridgeConfig["config"]["swversion"]
    url = "https://firmware.meethue.com/v1/checkupdate/?deviceTypeId=BSB002&version=" + swversion
    response = requests.get(url)
    if response.status_code == 200:
        device_data = json.loads(response.text)
        if len(device_data["updates"]) != 0:
            new_version = str(device_data["updates"][len(device_data["updates"])-1]["version"])
            new_versionName = str(device_data["updates"][len(device_data["updates"])-1]["versionName"])
            if new_version > swversion:
                logging.info("swversion number update from Philips, old: " + swversion + " new:" + new_version)
                bridgeConfig["config"]["swversion"] = new_version
                bridgeConfig["config"]["apiversion"] = new_versionName
                bridgeConfig["config"]["swupdate2"]["lastchange"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                bridgeConfig["config"]["swupdate2"]["bridge"]["lastinstall"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            else:
                logging.info("swversion higher than Philips")
        else:
            logging.info("no swversion number update from Philips")

def githubCheck():
    #creation_time = "2024-02-18 19:50:15.000000000 +0100\n"
    creation_time = subprocess.run("stat -c %y HueEmulator3.py", shell=True, capture_output=True, text=True)#2024-02-18 19:50:15.000000000 +0100\n
    creation_time_arg1 = creation_time.stdout.replace(".", " ").split(" ")#2024-02-18, 19:50:15, 000000000, +0100\n
    creation_time = creation_time_arg1[0] + " " + creation_time_arg1[1] + " " + creation_time_arg1[3].replace("\n", "")#2024-02-18 19:50:15 +0100
    creation_time = datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc).strftime("%Y-%m-%d %H")#2024-02-18 18

    url = "https://api.github.com/repos/diyhue/diyhue/branches/master"
    #url = "https://api.github.com/repos/hendriksen-mark/diyhue/branches/master"
    response = requests.get(url)
    if response.status_code == 200:
        device_data = json.loads(response.text)
        publish_time = datetime.strptime(device_data["commit"]["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H")

    logging.info("creation_time diyHue : " + str(creation_time))
    logging.info("publish_time  diyHue : " + str(publish_time))

    if publish_time > creation_time:
        logging.info("update on github")
        bridgeConfig["config"]["swupdate2"]["state"] = "allreadytoinstall"
        bridgeConfig["config"]["swupdate2"]["bridge"]["state"] = "allreadytoinstall"
    elif githubUICheck() == True:
        logging.info("UI update on github")
        bridgeConfig["config"]["swupdate2"]["state"] = "anyreadytoinstall"
        bridgeConfig["config"]["swupdate2"]["bridge"]["state"] = "anyreadytoinstall"
    else:
        logging.info("no update for diyHue or UI on github")
        bridgeConfig["config"]["swupdate2"]["state"] = "noupdates"
        bridgeConfig["config"]["swupdate2"]["bridge"]["state"] = "noupdates"

    bridgeConfig["config"]["swupdate2"]["checkforupdate"] = False

def githubUICheck():
    #creation_time = "2024-02-18 19:50:15.000000000 +0100\n"
    creation_time = subprocess.run("stat -c %y flaskUI/templates/index.html", shell=True, capture_output=True, text=True)#2024-02-18 19:50:15.000000000 +0100\n
    creation_time_arg1 = creation_time.stdout.replace(".", " ").split(" ")#2024-02-18, 19:50:15, 000000000, +0100\n
    creation_time = creation_time_arg1[0] + " " + creation_time_arg1[1] + " " + creation_time_arg1[3].replace("\n", "")#2024-02-18 19:50:15 +0100
    creation_time = datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc).strftime("%Y-%m-%d %H")#2024-02-18 18

    url = "https://api.github.com/repos/diyhue/diyhueUI/branches/master"
    #url = "https://api.github.com/repos/hendriksen-mark/diyhueUI/branches/master"
    response = requests.get(url)
    if response.status_code == 200:
        device_data = json.loads(response.text)
        publish_time = datetime.strptime(device_data["commit"]["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H")

    logging.info("creation_time UI : " + str(creation_time))
    logging.info("publish_time  UI : " + str(publish_time))

    if publish_time > creation_time:
        return True
    else:
        return False


def githubInstall_test():
    if bridgeConfig["config"]["swupdate2"]["state"] == "anyreadytoinstall":#ui update
        bridgeConfig["config"]["swupdate2"]["state"] = "installing"
        bridgeConfig["config"]["swupdate2"]["bridge"]["state"] = "installing"
        subprocess.Popen("sh githubUIInstall.sh",shell=True, close_fds=True)
    if bridgeConfig["config"]["swupdate2"]["state"] == "allreadytoinstall":#diyhue + ui update
        bridgeConfig["config"]["swupdate2"]["state"] = "installing"
        bridgeConfig["config"]["swupdate2"]["bridge"]["state"] = "installing"
        subprocess.Popen("sh githubInstall.sh",shell=True, close_fds=True)

def githubInstall():
    logging.info("work in progress")
    bridgeConfig["config"]["swupdate2"]["install"] = False
