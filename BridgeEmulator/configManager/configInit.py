import uuid
from random import randrange


def _generate_unique_id():
    rand_bytes = [randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])


def write_args(args, yaml_config):
    host_ip = args["HOST_IP"]
    ip_pieces = host_ip.split(".")
    yaml_config["config"]["ipaddress"] = host_ip
    yaml_config["config"]["gateway"] = ip_pieces[0] + "." + ip_pieces[1] + "." + ip_pieces[2] + ".1"
    yaml_config["config"]["mac"] = args["FULLMAC"]
    yaml_config["config"]["bridgeid"] = (args["MAC"][:6] + 'FFFE' + args["MAC"][-6:]).upper()
    return yaml_config


def generate_security_key(yaml_config):
    # generate security key for Hue Essentials remote access
    if not yaml_config["config"].get("Hue Essentials key"):
        yaml_config["config"]["Hue Essentials key"] = str(uuid.uuid1()).replace('-', '')
    return yaml_config
