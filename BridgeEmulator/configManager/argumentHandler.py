import argparse
from os import getenv
from subprocess import check_output
import logManager
import socket

logging = logManager.logger.get_logger(__name__)

def _getIpAddress():
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.connect(("8.8.8.8", 80))
   return s.getsockname()[0]

def get_environment_variable(var, boolean=False):
    value = getenv(var)
    if boolean and value:
        if value.lower() == "true":
            value = True
        else:
            value = False
    return value


def process_arguments(args):
    if not args["DEBUG"]:
        logManager.logger.configure_logger("INFO")
        logging.info("Debug logging disabled!")
    else:
        logging.info("Debug logging enabled!")


def parse_arguments():
    argumentDict = {"BIND_IP": '', "HOST_IP": '', "HTTP_PORT": '', "HTTPS_PORT": '', "FULLMAC": '', "MAC": '', "DEBUG": False, "DOCKER": False,
                    "IP_RANGE_START": '', "IP_RANGE_END": '', "DECONZ": '', "DECONZ_PORT": '', "scanOnHostIP": False, "disableOnlineDiscover": '', "noLinkButton": False, "noServeHttps": False}
    ap = argparse.ArgumentParser()

    # Arguements can also be passed as Environment Variables.
    ap.add_argument("--debug", action='store_true', help="Enables debug output")
    ap.add_argument("--bind-ip", help="The IP address to listen on", type=str)
    ap.add_argument("--ip", help="The IP address of the host system (Docker)", type=str)
    ap.add_argument("--http-port", help="The port to listen on for HTTP (Docker)", type=int)
    ap.add_argument("--mac", help="The MAC address of the host system (Docker)", type=str)
    ap.add_argument("--no-serve-https", action='store_true', help="Don't listen on port 443 with SSL")
    ap.add_argument("--ip-range", help="Set IP range for light discovery. Format: <START_IP>,<STOP_IP>", type=str)
    ap.add_argument("--scan-on-host-ip", action='store_true',
                    help="Scan the local IP address when discovering new lights")
    ap.add_argument("--deconz", help="Provide the IP address of your Deconz host. 127.0.0.1 by default.", type=str)
    ap.add_argument("--no-link-button", action='store_true',
                    help="DANGEROUS! Don't require the link button to be pressed to pair the Hue app, just allow any app to connect")
    ap.add_argument("--disable-online-discover", help="Disable Online and Remote API functions")

    args = ap.parse_args()

    if args.scan_on_host_ip:
        argumentDict["scanOnHostIP"] = True

    if args.no_link_button:
        argumentDict["noLinkButton"] = True

    if args.no_serve_https:
        argumentDict["noServeHttps"] = True

    if args.debug or get_environment_variable('DEBUG', True):
        argumentDict["DEBUG"] = True

    bind_ip = ''
    if args.bind_ip:
        bind_ip = args.bind_ip
    elif get_environment_variable('BIND_IP'):
        bind_ip = get_environment_variable('BIND_IP')
    argumentDict["BIND_IP"] = bind_ip

    if args.ip:
        host_ip = args.ip
    elif get_environment_variable('IP'):
        host_ip = get_environment_variable('IP')
    elif bind_ip:
        host_ip = bind_ip
    else:
        host_ip = _getIpAddress()
    argumentDict["HOST_IP"] = host_ip

    if args.http_port:  # should be depreciated
        host_http_port = args.http_port
    elif get_environment_variable('HTTP_PORT'):
        host_http_port = get_environment_variable('HTTP_PORT')
    else:
        host_http_port = 80
    host_https_port = 443
    argumentDict["HTTP_PORT"] = host_http_port
    argumentDict["HTTPS_PORT"] = host_https_port
    logging.info("Using Host %s:%s" % (host_ip, host_http_port))

    if args.mac:
        full_mac_string = args.mac  # keeps : for cert generation
        mac = str(args.mac).replace(":", "")
    elif get_environment_variable('MAC'):
        full_mac_string = get_environment_variable('MAC')
        mac = str(full_mac_string).replace(":", "")
    else:
        full_mac_string = check_output("cat /sys/class/net/$(ip -o addr | grep %s | awk '{print $2}')/address" % host_ip,
                                 shell=True).decode('utf-8')[:-1]
        mac = str(full_mac_string).replace(":", "")

    argumentDict["FULLMAC"] = full_mac_string
    argumentDict["MAC"] = mac
    logging.info("Host MAC given as " + mac)

    if args.ip_range or get_environment_variable('IP_RANGE'):
        if args.ip_range:
            ranges = args.ip_range
        else:
            ranges = get_environment_variable('IP_RANGE')
        ranges = ranges.split(',')
        if ranges[0] and int(ranges[0]) >= 0:
            ip_range_start = int(ranges[0])
        else:
            ip_range_start = 0

        if ranges[1] and int(ranges[1]) > 0:
            ip_range_end = int(ranges[1])
        else:
            ip_range_end = 255
    elif get_environment_variable('IP_RANGE_START') and get_environment_variable('IP_RANGE_END'):
        ip_range_start = get_environment_variable('IP_RANGE_START')
        ip_range_end = get_environment_variable('IP_RANGE_END')
    else:
        ip_range_start = 0
        ip_range_end = 255
    argumentDict["IP_RANGE_START"] = ip_range_start
    argumentDict["IP_RANGE_END"] = ip_range_end
    logging.info("IP range for light discovery: " + str(ip_range_start) + "-" + str(ip_range_end))

    if args.deconz:
        deconz_ip = args.deconz
    elif get_environment_variable('DECONZ'):
        deconz_ip = get_environment_variable('DECONZ')
    else:
        deconz_ip = "127.0.0.1"
    argumentDict["DECONZ"] = deconz_ip
    logging.info("Deconz IP given as " + deconz_ip)

    if get_environment_variable("DECONZ_PORT"):
        argumentDict["DECONZ_PORT"] = get_environment_variable("DECONZ_PORT")

    if args.disable_online_discover or get_environment_variable('disableonlinediscover'):
        disableOnlineDiscover = True
        logging.info("Online Discovery/Remote API Disabled!")
    else:
        disableOnlineDiscover = False
        logging.info("Online Discovery/Remote API Enabled!")
    argumentDict["disableOnlineDiscover"] = disableOnlineDiscover

    return argumentDict
