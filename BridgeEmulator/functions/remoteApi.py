import requests
import base64
import urllib.parse
import json
from pprint import pprint

def remoteApi(users):
    url = 'http://185.162.65.24:81/devices'
    while True:
        userlist = ''
        for user in users.keys():
            userlist += user + ','
        response = requests.get(url + '?data=' + base64.urlsafe_b64encode(bytes(userlist.rstrip(','), "utf8")).decode("utf-8"), timeout=35)
        if response.status_code == 200:
            if  response.text != '{renew}':
                data = json.loads(response.text)
                pprint(data)
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
            print("error: " + str(response.status_code) + ", " + response.text)
            sleep(5) # don't overload the remote server
