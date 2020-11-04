import logManager
import requests
from time import sleep

logging = logManager.logger.get_logger(__name__)

def remoteDiscover(config):
    url = 'https://discovery.diyhue.org'
    while True:
        try:
            payload = {"id": config["bridgeid"],"internalipaddress": config["ipaddress"],"macaddress": config["mac"],"name": config["name"]}
            response = requests.post(url, timeout=5, json=payload)
            print(response.text)
            sleep(30)
        except:
                logging.debug("remote sever is down")
                sleep(60) # don't overload the remote server
