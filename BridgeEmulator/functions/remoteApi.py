import logging
import requests
import base64
import urllib.parse
import json
from time import sleep

def remoteApi(users):
    url = 'https://remote.diyhue.org/devices'
    while True:
        try:
            userlist = ''
            for user in users.keys():
                userlist += user + ','
            response = requests.get(url + '?data=' + base64.urlsafe_b64encode(bytes(userlist.rstrip(','), "utf8")).decode("utf-8"), timeout=35)
            if response.status_code == 200:
                if  response.text != '{renew}':
                    data = json.loads(response.text)
                    if data["method"] == 'GET':
                        bridgeReq = requests.get('http://localhost/' + data["address"], timeout=5)
                        requests.post(url + '/' + data["address"].split('/')[1], timeout=5, json=json.loads(bridgeReq.text))
                    if data["method"] == 'POST':
                        bridgeReq = requests.post('http://localhost/' + data["address"], json=data["body"], timeout=5)
                        requests.post(url + '/' + data["address"].split('/')[1], timeout=5, json=json.loads(bridgeReq.text))
                    if data["method"] == 'PUT':
                        bridgeReq = requests.put('http://localhost/' + data["address"], json=data["body"], timeout=5)
                        requests.post(url + '/' + data["address"].split('/')[1], timeout=5, json=json.loads(bridgeReq.text))

            else:
                logging.debug("remote server error: " + str(response.status_code) + ", " + response.text)
                sleep(30) # don't overload the remote server
        except:
                logging.debug("remote sever is down")
                sleep(60) # don't overload the remote server
            
