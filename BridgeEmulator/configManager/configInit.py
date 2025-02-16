import logManager
import uuid
from random import randrange
import subprocess
from typing import Dict, Any
logging = logManager.logger.get_logger(__name__)

def _generate_unique_id():
    rand_bytes = [randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def _get_default_gateway() -> str:
    """
    Get the default gateway IP address.
    
    Returns:
        str: The default gateway IP address or None if not found.
    """
    result = subprocess.run(
        ["ip route | grep default | head -n 1 | cut -d ' ' -f 3"],
        shell=True,
        capture_output=True, 
        text=True
    )
    default_route = next((line for line in result.stdout.splitlines() if "default" in line), None)
    return default_route.split()[2] if default_route else None

def write_args(args, yaml_config):

    gateway_ip = _get_default_gateway()
    host_ip = args["HOST_IP"]
    ip_pieces = gateway_ip if gateway_ip else f"{host_ip.rsplit('.', 1)[0]}.1"

    yaml_config["config"]["ipaddress"] = host_ip
    yaml_config["config"]["gateway"] = ip_pieces
    yaml_config["config"]["mac"] = args["FULLMAC"]
    yaml_config["config"]["bridgeid"] = (args["MAC"][:6] + 'FFFE' + args["MAC"][-6:]).upper()
    return yaml_config

def generate_security_key(yaml_config):
    # generate security key for Hue Essentials remote access
    if not yaml_config["config"].get("Hue Essentials key"):
        yaml_config["config"]["Hue Essentials key"] = str(uuid.uuid1()).replace('-', '')
    return yaml_config
