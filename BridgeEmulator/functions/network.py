import logging
import socket
import sys
import argparse

def getIpAddress():
   if args.ip:
      return args.ip
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.connect(("8.8.8.8", 80))
   return s.getsockname()[0]

