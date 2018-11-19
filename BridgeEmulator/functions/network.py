import logging
import socket
import sys


def getIpAddress():
    if len(sys.argv) == 3:
       return sys.argv[2]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

