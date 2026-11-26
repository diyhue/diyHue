import logManager
import requests
from time import sleep

logging = logManager.logger.get_logger(__name__)

### This service is needed for Hue Essentials to automatically discover the diyhue instance.

def runRemoteDiscover(config):
    logging.info("Starting discovery service")
    url = 'https://discovery.diyhue.org'
    while True:
        if config.get("discovery", True) == False:
            sleep(60)  # disabled, can be turned on again at runtime
            continue
        try:
            payload = {"id": config["bridgeid"],"internalipaddress": config["ipaddress"],"macaddress": config["mac"],"name": config["name"]}
            response = requests.post(url, timeout=5, json=payload)
            sleep(60)
        except:
                logging.debug("Remote sever is down")
                sleep(60) # don't overload the remote server
