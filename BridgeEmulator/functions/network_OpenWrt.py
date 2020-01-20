import os
import socket

if os.name != "nt":
    import fcntl
    import struct

    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                                bytes(ifname[:15], 'utf-8')))[20:24])

def getIpAddress():
    ip = None

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except:
        pass
    
    if (not ip or ip.startswith("127.")) and os.name != "nt":
        interfaces = [
            "br0",
            "br-lan",
            "eth0",
            "eth1",
            "eth2",
            "wlan0",
            "wlan1",
            "wifi0",
            "ath0",
            "ath1",
            "ppp0",
            ]
        for ifname in interfaces:
            try:
                ip = get_interface_ip(ifname)
                break
            except IOError:
                pass
    return ip
