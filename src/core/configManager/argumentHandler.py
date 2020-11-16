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


def get_argument(env_var, boolean=False, args=None, default=None):
    if args:
        if boolean:
            return True
        else:
            return args
    elif get_environment_variable(env_var, boolean):
        return get_environment_variable(env_var, boolean)
    elif boolean:
        return False
    else:
        return default

def parse_arguments():
    # argumentDict = {"BIND_IP": '', "HOST_IP": '', "HTTP_PORT": '', "HTTPS_PORT": '', "FULLMAC": '', "MAC": '', "DEBUG": False, "DOCKER": False,
    #                 "IP_RANGE_START": '', "IP_RANGE_END": '', "DECONZ": '', "DECONZ_PORT": '', "scanOnHostIP": False, "disableOnlineDiscover": '',
    #                 "noLinkButton": False, "noServeHttps": False, "CONFIG_BACKUPS": 25, "CERT_BACKUPS": 25}
    argumentDict = {}
    ap = argparse.ArgumentParser()

    ap.add_argument("--debug", action='store_true', help="Enables debug output")
    ap.add_argument("--bind-ip", help="The IP address to listen on", type=str)
    ap.add_argument("--ip", help="The IP address of the host system", type=str)
    ap.add_argument("--http-port", help="The port to listen on for HTTP", type=int)
    ap.add_argument("--mac", help="The MAC address of the host system", type=str)
    ap.add_argument("--no-serve-https", action='store_true', help="Don't listen on port 443 with SSL")
    ap.add_argument("--ip-range-start", help="Set IP range for light discovery. Must use both start and end!", type=str)
    ap.add_argument("--ip-range-end", help="Set IP range for light discovery. Must use both start and end!", type=str)
    ap.add_argument("--scan-on-host-ip", action='store_true',
                    help="Scan the local IP address when discovering new lights")
    ap.add_argument("--deconz", help="Provide the IP address of your Deconz host. 127.0.0.1 by default.", type=str)
    ap.add_argument("--no-link-button", action='store_true',
                    help="DANGEROUS! Don't require the link button to be pressed to pair the Hue app, just allow any app to connect")
    ap.add_argument("--disable-online-discover", help="Disable Online and Remote API functions")
    ap.add_argument("--config-max-backups", help="Maximum config backups to be stored")
    ap.add_argument("--certificate-max-backups", help="Maximum certificate backups to be stored")
    ap.add_argument("--config-location", help="Location where config files are stored")
    ap.add_argument("--install-location", help="Installation location of diyHue")

    args = ap.parse_args()

    argumentDict["scanOnHostIP"] = get_argument("scanOnHostIP", boolean=True, args=args.scan_on_host_ip)
    argumentDict["noLinkButton"] = get_argument("noLinkButton", boolean=True, args=args.no_link_button)
    argumentDict["noServeHttps"] = get_argument("noServeHttps", boolean=True, args=args.no_serve_https)
    argumentDict["DEBUG"] = get_argument("DEBUG", boolean=True, args=args.debug)
    argumentDict["BIND_IP"] = get_argument("BIND_IP", args=args.bind_ip, default='')
    argumentDict["HOST_IP"] = get_argument("HOST_IP", args=args.ip)
    if not argumentDict["HOST_IP"]:
        if argumentDict["BIND_IP"]:
            argumentDict["HOST_IP"] = argumentDict["BIND_IP"]
        else:
            argumentDict["HOST_IP"] = _getIpAddress()

    argumentDict["HTTP_PORT"] = get_argument("HTTP_PORT", boolean=False, args=args.http_port, default=80) # should be depreciated
    argumentDict["HTTPS_PORT"] = get_argument("HTTP_PORT", default=443)
    logging.info("Using Host %s:%s" % (argumentDict["HOST_IP"], argumentDict["HTTP_PORT"]))
    argumentDict["FULLMAC"] = get_argument("MAC", args=args.mac)
    if not argumentDict["FULLMAC"]:
        argumentDict["FULLMAC"] = \
            check_output("cat /sys/class/net/$(ip -o addr | grep %s | awk '{print $2}')/address" % argumentDict["HOST_IP"],
                shell=True).decode('utf-8')[:-1]
    argumentDict["MAC"] = str(argumentDict["FULLMAC"]).replace(":", "")
    logging.info("Host MAC given as " + argumentDict["MAC"])

    argumentDict["IP_RANGE_START"] = get_argument('IP_RANGE_START', args=args.ip_range_start, default=0)
    argumentDict["IP_RANGE_END"] = get_argument('IP_RANGE_END', args=args.ip_range_end, default=255)
    logging.info("IP range for light discovery: " + str(argumentDict["IP_RANGE_START"]) + "-" + str(argumentDict["IP_RANGE_END"]))

    argumentDict["DECONZ"] = get_argument('DECONZ', args=args.deconz, default="127.0.0.1")
    logging.info("Deconz IP given as " + argumentDict["DECONZ"])

    argumentDict["DECONZ_PORT"] = get_argument("DECONZ_PORT")
    argumentDict["disableOnlineDiscover"] = get_argument('disableonlinediscover', args=args.disable_online_discover, boolean=True, default=False)
    logging.info("Online Discovery/Remote API: " + str(not argumentDict["disableOnlineDiscover"]))

    argumentDict["CONFIG_BACKUPS"] = int(get_argument("CONFIG_BACKUPS", args=args.config_max_backups, default=25))
    argumentDict["CERT_BACKUPS"] = int(get_argument("CERT_BACKUPS", args=args.certificate_max_backups, default=25))

    argumentDict["CONFIG_LOCATION"] = get_argument("CONFIG_LOCATION", args=args.config_location, default="/config")
    argumentDict["INSTALL_LOCATION"] = get_argument("INSTALL_LOCATION", args=args.install_location, default="/diyhue")

    return argumentDict
