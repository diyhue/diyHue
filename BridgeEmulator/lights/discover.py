import logManager
import configManager
import socket
import json
from time import sleep
from services.deconz import scanDeconz
from threading import Thread
from lights.protocols import mqtt, yeelight, native, native_single, native_multi, tasmota, shelly, esphome, tradfri

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.json_config
newLights = configManager.runtimeConfig.newLights


def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
    result = sock.connect_ex((host, port))
    sock.close()
    return result

def iter_ips(port):
    argsDict = configManager.runtimeConfig.arg
    HOST_IP = argsDict["HOST_IP"]
    scan_on_host_ip = argsDict["scanOnHostIP"]
    ip_range_start = argsDict["IP_RANGE_START"]
    ip_range_end = argsDict["IP_RANGE_END"]
    host = HOST_IP.split('.')
    if scan_on_host_ip:
        yield ('127.0.0.1', port)
        return
    for addr in range(ip_range_start, ip_range_end + 1):
        host[3] = str(addr)
        test_host = '.'.join(host)
        if test_host != HOST_IP:
            yield (test_host, port)

def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts


def scanForLights(): #scan for ESP8266 lights and strips
    #return all host that listen on port 80
    device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    Thread(target=mqtt.discover).start()
    Thread(target=yeelight.discover).start()
    Thread(target=native_multi.discover, args=[device_ips]).start() # native_multi probe all esp8266 lights with firmware from diyhue repo
    sleep(0.2) # wait half second to not send http requsts in the same time for the same device during multple protocols probe.
    Thread(target=tasmota.discover, args=[device_ips]).start()
    sleep(0.2)
    Thread(target=shelly.discover, args=[device_ips]).start()
    sleep(0.2)
    Thread(target=esphome.discover, args=[device_ips]).start()
    Thread(target=tradfri.discover).start()
    scanDeconz()
    configManager.bridgeConfig.save_config()
