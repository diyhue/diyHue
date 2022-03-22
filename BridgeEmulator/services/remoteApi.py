import logManager
import requests
import base64
import urllib.parse
import json
from time import sleep

logging = logManager.logger.get_logger(__name__)

def runRemoteApi(BIND_IP, config):
    if BIND_IP == '':
        ip = "localhost"
    else:
        ip = BIND_IP
    url = 'https://remote.diyhue.org/devices'
    while True:
        if config["Remote API enabled"]:
            try:
                response = requests.get(url + '?apikey=' + base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8"), timeout=35)
                if response.status_code == 200:
                    if  response.text != '{renew}':
                        data = json.loads(response.text)
                        if data["method"] == 'GET':
                            bridgeReq = requests.get(f'http://{ip}/' + data['address'], timeout=5)
                            requests.post(url + '?apikey=' + base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8"), timeout=5, json=json.loads(bridgeReq.text))
                        if data["method"] == 'POST':
                            bridgeReq = requests.post(f'http://{ip}/' + data['address'], json=data["body"], timeout=5)
                            requests.post(url + '?apikey=' + base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8"), timeout=5, json=json.loads(bridgeReq.text))
                        if data["method"] == 'PUT':
                            bridgeReq = requests.put(f'http://{ip}/' + data['address'], json=data["body"], timeout=5)
                            requests.post(url + '?apikey=' + base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8"), timeout=5, json=json.loads(bridgeReq.text))

                else:
                    logging.debug("remote server error: " + str(response.status_code) + ", " + response.text)
                    sleep(30) # don't overload the remote server
            except:
                    logging.debug("remote sever is down")
                    sleep(60) # don't overload the remote server
        else:
            sleep(10) #sleep if remote access is not enabled
