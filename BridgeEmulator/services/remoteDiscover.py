import logManager
import requests
import json
from time import sleep

logging = logManager.logger.get_logger(__name__)

def runRemoteDiscover(config):
    print("Starting remote discovery")
    url = 'https://discovery.diyhue.org'
    while True:
        try:
            logging.debug("Discovery ping")
            payload = {"id": config["bridgeid"],"internalipaddress": config["ipaddress"],"macaddress": config["mac"],"name": config["name"]}
            response = requests.post(url, timeout=5, json=payload)
            sleep(60)
        except:
                logging.debug("Remote sever is down")
                sleep(60) # don't overload the remote server
