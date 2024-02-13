import logManager
import uuid
import netifaces
from random import randrange
logging = logManager.logger.get_logger(__name__)

def _generate_unique_id():
    rand_bytes = [randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def write_args(args, yaml_config):
    host_ip = args['HOST_IP']

    devices = []
    for interface in netifaces.interfaces():
        for family, addresses in netifaces.ifaddresses(interface).items():
            if family not in (netifaces.AF_INET, netifaces.AF_INET6):
                continue
            for address in addresses:
                if address['addr'] == host_ip:
                   devices.append((family, interface))
    logging.debug('Found network devices ' + str(devices))

    gateway_ips = []
    for family, gateways in netifaces.gateways().items():
        for device in devices:
            if family != device[0]:
                continue
            for gateway in gateways:
                if gateway[1] == device[1]:
                    gateway_ips.append(gateway[0])
    logging.debug('Found gateways ' + str(gateway_ips))

    if not gateway_ips:
        ip_pieces = host_ip.split('.')
        gateway_ips.append(ip_pieces[0] + '.' + ip_pieces[1] + '.' + ip_pieces[2] + '.1')
        logging.info('Found no gateways and use fallback ' + str(gateway_ips))

    yaml_config['config']['ipaddress'] = host_ip
    yaml_config['config']['gateway'] = gateway_ips[0]
    yaml_config['config']['mac'] = args['FULLMAC']
    yaml_config['config']['bridgeid'] = (args['MAC'][:6] + 'FFFE' + args['MAC'][-6:]).upper()
    return yaml_config

def generate_security_key(yaml_config):
    # generate security key for Hue Essentials remote access
    if not yaml_config["config"].get("Hue Essentials key"):
        yaml_config["config"]["Hue Essentials key"] = str(uuid.uuid1()).replace('-', '')
    return yaml_config
