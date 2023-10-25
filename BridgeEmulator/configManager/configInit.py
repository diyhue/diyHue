import ipaddress
import uuid
from random import randrange


def _generate_unique_id():
    rand_bytes = [randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])


def write_args(args, yaml_config):
    host_ip = args["HOST_IP"]

    parsed_ip = ipaddress.ip_address(host_ip)
    netmask = yaml_config["config"]["netmask"]
    network = ipaddress.ip_network(f'{parsed_ip}/{netmask}', False)
    gateway = args.get("GATEWAY", network.network_address + 1)

    yaml_config["config"]["ipaddress"] = host_ip
    yaml_config["config"]["gateway"] = gateway
    yaml_config["config"]["mac"] = args["FULLMAC"]
    yaml_config["config"]["bridgeid"] = (args["MAC"][:6] + 'FFFE' + args["MAC"][-6:]).upper()
    return yaml_config


def generate_security_key(yaml_config):
    # generate security key for Hue Essentials remote access
    if not yaml_config["config"].get("Hue Essentials key"):
        yaml_config["config"]["Hue Essentials key"] = str(uuid.uuid1()).replace('-', '')
    return yaml_config
