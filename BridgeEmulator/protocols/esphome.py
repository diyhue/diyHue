import json
import logging
import random
import requests

import socket
import sys

from time import sleep
from subprocess import check_output
from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy
from functions.network import getIpAddress

def getRequest(url, timeout=3):

    head = {"Content-type": "application/json"}
    response = requests.get(url, timeout=timeout, headers=head)
    return response.text

def postRequest(url, timeout=3)
    head = {"Content-type": "application/json"}
    response = requests.post(url, timeout=3, headers=head)
    return response.text


#response = requests.get('http://light2.local/light/white_led', timeout=3, headers=head)
#response = requests.post('http://light2.local/light/white_led/turn_on?brightness=255&transition=0.4&color_temp=370', timeout=3, headers=head)
#response = requests.post('http://light2.local/light/white_led/turn_off', timeout=3, headers=head)
#requests.post('http://light2.local/light/color_led/turn_on?brightness=255&transition=0.4&r=136&g=65&b=217', timeout=3, headers=head)
#response = requests.get('http://light2.local/light/color_led', timeout=3, headers=head)
#print(response.text)
