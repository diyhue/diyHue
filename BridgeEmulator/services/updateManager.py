import requests
import configManager
import logManager
import json
from datetime import datetime

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
            logging.info("no swversion number update")

def githubCheck():
    logging.debug("work in process")