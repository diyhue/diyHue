import argparse
import logManager
from os import getenv, path
from functions.network import getIpAddress
from subprocess import check_output, call

logging = logManager.logger.get_logger(__name__)

def get_environment_variable(var, boolean=False):
    value = getenv(var)
    if boolean and value:
        if value.lower() == "true":
            value = True
        else:
            value = False
    return value


def generate_certificate(mac, path):
    logging.info("Generating certificate")
    serial = (mac[:6] + "fffe" + mac[-6:]).encode('utf-8')
    call(["/usr/bin/env", "bash", "/opt/hue-emulator/genCert.sh", serial, path])
    logging.info("Certificate created")


def process_arguments(configDir, args):
    if not args["DEBUG"]:
        logManager.logger.configure_logger("INFO")
        logging.info("Debug logging disabled!")
    else:
        logging.info("Debug logging enabled!")
    if not path.isfile(configDir + "/cert.pem"):
        generate_certificate(args["MAC"], configDir)


def parse_arguments():
    argumentDict = {"BIND_IP": '', "HOST_IP": '', "HTTP_PORT": '', "HTTPS_PORT": '', "FULLMAC": '', "MAC": '', "DEBUG": False, "DOCKER": False,
                    "noLinkButton": False, "noServeHttps": False}
    ap = argparse.ArgumentParser()

    # Arguements can also be passed as Environment Variables.
    ap.add_argument("--debug", action='store_true', help="Enables debug output")
    ap.add_argument("--bind-ip", help="The IP address to listen on", type=str)
    ap.add_argument("--config_path", help="Set certificate and config files location", type=str)
    ap.add_argument("--docker", action='store_true', help="Enables setup for use in docker container")
    ap.add_argument("--ip", help="The IP address of the host system (Docker)", type=str)
    ap.add_argument("--http-port", help="The port to listen on for HTTP (Docker)", type=int)
    ap.add_argument("--https-port", help="The port to listen on for HTTPS (Docker)", type=int)
    ap.add_argument("--mac", help="The MAC address of the host system (Docker)", type=str)
    ap.add_argument("--no-serve-https", action='store_true', help="Don't listen on port 443 with SSL")
    ap.add_argument("--ip-range", help="Deprecated use webui, Set IP range for light discovery. Format: <START_IP>,<STOP_IP>", type=str)
    ap.add_argument("--sub-ip-range", help="Deprecated use webui, Set SUB IP range for light discovery. Format: <START_IP>,<STOP_IP>", type=str)
    ap.add_argument("--scan-on-host-ip", action='store_true', help="Deprecated use webui, Scan the local IP address when discovering new lights")
    ap.add_argument("--deconz", help="Deprecated use webui, Provide the IP address of your Deconz host. 127.0.0.1 by default.", type=str)
    ap.add_argument("--no-link-button", action='store_true',
                    help="DANGEROUS! Don't require the link button to be pressed to pair the Hue app, just allow any app to connect")
    ap.add_argument("--disable-online-discover", help="Deprecated use webui, Disable Online and Remote API functions")
    ap.add_argument("--TZ", help="Deprecated use webui, Set time zone", type=str)

    args = ap.parse_args()

    if args.scan_on_host_ip:
        logging.warn("scan_on_host_ip is Deprecated in commandline and not active, please setup via webui")

    if args.no_link_button:
        argumentDict["noLinkButton"] = True

    if args.no_serve_https:
        argumentDict["noServeHttps"] = True

    if args.debug or get_environment_variable('DEBUG', True):
        argumentDict["DEBUG"] = True

    if args.config_path:
        config_path = args.config_path
    elif get_environment_variable('CONFIG_PATH'):
        config_path = get_environment_variable('CONFIG_PATH')
    else:
        config_path = '/opt/hue-emulator/config'
    argumentDict["CONFIG_PATH"] = config_path

    if args.bind_ip:
        bind_ip = args.bind_ip
    elif get_environment_variable('BIND_IP'):
        bind_ip = get_environment_variable('BIND_IP')
    else:
        bind_ip = '0.0.0.0'
    argumentDict["BIND_IP"] = bind_ip

    if args.TZ or get_environment_variable('TZ'):
        logging.warn("Time Zone is Deprecated in commandline and not active, please setup via webui")

    if args.ip:
        host_ip = args.ip
    elif get_environment_variable('IP'):
        host_ip = get_environment_variable('IP')
    elif bind_ip != '0.0.0.0':
        host_ip = bind_ip
    else:
        host_ip = getIpAddress()
    argumentDict["HOST_IP"] = host_ip

    if args.http_port:
        host_http_port = args.http_port
    elif get_environment_variable('HTTP_PORT'):
        host_http_port = int(get_environment_variable('HTTP_PORT'))
    else:
        host_http_port = 80
    argumentDict["HTTP_PORT"] = host_http_port

    if args.https_port:
        host_https_port = args.https_port
    elif get_environment_variable('HTTPS_PORT'):
        host_https_port = int(get_environment_variable('HTTPS_PORT'))
    else:
        host_https_port = 443
    argumentDict["HTTPS_PORT"] = host_https_port

    logging.info("Using Host %s:%s" % (host_ip, host_http_port))
    logging.info("Using Host %s:%s" % (host_ip, host_https_port))

    if args.mac and str(args.mac).replace(":", "").capitalize != "XXXXXXXXXXXX":
        dockerMAC = args.mac  # keeps : for cert generation
        mac = str(args.mac).replace(":", "")
    elif get_environment_variable('MAC') and get_environment_variable('MAC').strip('\u200e').replace(":", "").capitalize != "XXXXXXXXXXXX":
        dockerMAC = get_environment_variable('MAC').strip('\u200e')
        mac = str(dockerMAC).replace(":", "")
    else:
        dockerMAC = check_output("cat /sys/class/net/$(ip -o addr | grep %s | awk '{print $2}')/address" % host_ip,
                                 shell=True).decode('utf-8')[:-1]
        mac = str(dockerMAC).replace(":", "")

    if args.docker or get_environment_variable('DOCKER', True):
        docker = True
    else:
        docker = False
    argumentDict["FULLMAC"] = dockerMAC
    argumentDict["MAC"] = mac
    argumentDict["DOCKER"] = docker
    if mac.capitalize == "XXXXXXXXXXXX" or mac == "":
        logging.exception("No valid MAC address provided " + str(mac))
        logging.exception("To fix this visit: https://diyhue.readthedocs.io/en/latest/getting_started.html")
        raise SystemExit("CRITICAL! No valid MAC address provided " + str(mac))
    else:
        logging.info("Host MAC given as " + mac)

    if args.ip_range or get_environment_variable('IP_RANGE') or args.sub_ip_range or get_environment_variable('IP_RANGE_START') and get_environment_variable('IP_RANGE_END') or get_environment_variable('SUB_IP_RANGE') or get_environment_variable('SUB_IP_RANGE_START') or get_environment_variable('SUB_IP_RANGE_END'):
        logging.warn("IP range is Deprecated in commandline and not active, please setup via webui")

    if args.deconz or get_environment_variable('DECONZ'):
        logging.warn("DECONZ is Deprecated in commandline and not active, please setup via webui")

    if args.disable_online_discover or get_environment_variable('disableonlinediscover'):
        logging.warn("disableonlinediscover is Deprecated in commandline and not active, please setup via webui")

    if argumentDict['noServeHttps']:
        logging.info("HTTPS Port Disabled")

    return argumentDict
