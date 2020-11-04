import base64
import json
import logging
from time import sleep

import requests


def remoteApi(BIND_IP, config):
    ip = "localhost"
    if BIND_IP !=  '':
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
                            bridgeReq = requests.get('http://%s/%s' % (ip, data['address']), timeout=5)
                            requests.post(url + '?apikey=' + base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8"), timeout=5, json=json.loads(bridgeReq.text))
                        elif data["method"] == 'POST':
                            bridgeReq = requests.post('http://%s/%s' % (ip, data['address']), json=data["body"], timeout=5)
                            requests.post(url + '?apikey=' + base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8"), timeout=5, json=json.loads(bridgeReq.text))
                        elif data["method"] == 'PUT':
                            bridgeReq = requests.put('http://%s/%s' % (ip, data['address']), json=data["body"], timeout=5)
                            requests.post(url + '?apikey=' + base64.urlsafe_b64encode(bytes(config["Hue Essentials key"], "utf8")).decode("utf-8"), timeout=5, json=json.loads(bridgeReq.text))

                else:
                    logging.info("remote server error: " + str(response.status_code) + ", " + response.text)
                    sleep(30) # don't overload the remote server
            except:
                    logging.info("remote sever is down")
                    sleep(60) # don't overload the remote server
        else:
            sleep(10) #sleep if remote access is not enabled
