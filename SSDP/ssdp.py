#!/usr/bin/python
import socket
import sys
import struct
import random
from time import time, sleep
from uuid import getnode as get_mac

mac = '%012x' % get_mac()

SSDP_ADDR = '239.255.255.250'
SSDP_PORT = 1900
MSEARCH_Interval = 2
multicast_group_c = SSDP_ADDR
multicast_group_s = (SSDP_ADDR, SSDP_PORT)
server_address = ('', SSDP_PORT)

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

Response_message = 'HTTP/1.1 200 OK\r\nHOST: 239.255.255.250:1900\r\nEXT:CACHE-CONTROL: max-age=100\r\nLOCATION: http://' + get_ip_address() + ':80/description.xml\r\nSERVER: Linux/3.14.0 UPnP/1.0 IpBridge/1.16.0\r\nhue-bridgeid: ' + mac.upper() + '\r\nST: urn:schemas-upnp-org:device:basic:1\r\nUSN: uuid:2f402f80-da50-11e1-9b23-' + mac

print Response_message
#waits to recieve a MSearch mesagge. If a right message is recieved , calls callbackfun
def ssdp_search(timeout=5):
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)
    # add the socket to the multicast group on all interfaces.
    group = socket.inet_aton(multicast_group_c)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
	      print >>sys.stderr, '\n waiting to recieve'
	      data, address = sock.recvfrom(1024)    
	      print >>sys.stderr, 'received %s bytes from %s' % (len(data), address)
              print >>sys.stderr, data

	      #discard message if header is not in right format 
	      if data[0:19]== 'M-SEARCH * HTTP/1.1':
		   if data.find("ssdp:all") != -1: 
			  callbackfun()
			  mxpos = data.find("MX:") 
			  maxdelay = int(data[mxpos+3]) % 5   #Max value of this field is 5 			
			  sleep(random.randrange(0, maxdelay+1, 1))  #wait for random 0-MX time until sending out responses using unicast.
			  print >>sys.stderr, 'Sending M Search response to - ', address
    			  sock.sendto(Response_message, address)
		   else:
                       print >>sys.stderr, 'MSearch with ST field != ssdp:all'
              else:
	           print >>sys.stderr, 'recieved wrong MSearch'
	      sleep(timeout)

#Sends out SSDP M Search messages in a while(1) loop
def ssdp_broadcast():
    # Create the datagram socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set a timeout so the socket does not block indefinitely when trying
    # to receive data.
    sock.settimeout(MSEARCH_Interval+0.5)
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    while True:
	  print >>sys.stderr, 'Sending M Search ....'
	  sent = sock.sendto(message,multicast_group_s)
	  try:
              data, server = sock.recvfrom(1024)
          except socket.timeout:
              print >>sys.stderr, 'timed out '
          else:
	      print >>sys.stderr, 'received "%s" from %s' % (data, server)   

def callbackfun():
    print >>sys.stderr, '\n In callback'

if __name__ == '__main__':
    port = ssdp_search()
