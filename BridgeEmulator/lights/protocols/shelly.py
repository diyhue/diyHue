import json
import logManager
import requests

logging = logManager.logger.get_logger(__name__)

#bridgeConfig = configManager.bridgeConfig.yaml_config
#newLights = configManager.runtimeConfig.newLights

def discover(detectedLights, device_ips):
    logging.debug('shelly: <discover> invoked!')
    for ip in device_ips:
        try:
            logging.debug('shelly: probing ip ' + ip)
            response = requests.get('http://' + ip + '/shelly', timeout = 5)
            if response.status_code == 200:
                logging.debug('Shelly: ' + ip + ' is a shelly device ')
                device_data = json.loads(response.text)

                device_model = ''
                if (not 'gen' in device_data) and ('type' in device_data):
                    device_model = device_data['type']
                elif ('gen' in device_data) and ('model' in device_data):
                    device_model = device_data['model']
                else:
                    logging.info('Shelly: <discover> not implemented api version!')

                if (device_model == 'SHSW-1') or (device_model == 'SHSW-PM'):
                    shelly_data = request_api_v1(ip, 'status')
                    logging.debug('Shelly: IP: ' + shelly_data['wifi_sta']['ip'])
                    logging.debug('Shelly: MAC: ' + shelly_data['mac'])

                    config = {'ip': ip, 'mac': shelly_data['mac'], 'gen': 1}

                    shelly_data = request_api_v1(ip, 'settings')
                    name = shelly_data['name'] if 'name' in shelly_data else ip
                    name = name.strip() if name.strip() != '' else ip
                    detectedLights.append({'protocol': 'shelly', 'name': name, 'modelid': 'LOM001', 'protocol_cfg': config})
                elif (device_model == 'SNSW-001P8EU'):
                    shelly_data = request_api_v2(ip, 'WiFi.GetStatus')
                    logging.debug('Shelly: IP: ' + shelly_data['sta_ip'])
                    shelly_data = request_api_v2(ip, 'Shelly.GetDeviceInfo')
                    logging.debug('Shelly: MAC: ' + shelly_data['mac'])

                    config = {'ip': ip, 'mac': shelly_data['mac'], 'gen': device_data['gen'] }

                    name = shelly_data['name'] if 'name' in shelly_data else ip
                    name = name.strip() if name.strip() != '' else ip
                    detectedLights.append({'protocol': 'shelly', 'name': name, 'modelid': 'LOM001', 'protocol_cfg': config})
                else:
                    logging.info('Shelly: ' + ip + ' is not supported ')
        except Exception as exception:
            logging.debug('Shelly: IP ' + ip + ' is unknown device, ' + str(exception))

def set_light(light, data):
    config = light.protocol_cfg
    logging.debug('Shelly: <set_light> invoked! IP=' + config['ip'])

    for key, value in data.items():
        if key == 'on':
            if (not 'gen' in config) or (config['gen'] == 1):
                request_api_v1(config['ip'], 'relay/0?turn=' + ('on' if value else 'off'))
            elif (config['gen'] == 2) or (config['gen'] == 3):
                request_api_v2(config['ip'], 'Switch.Set?id=0&on=' + str(value).lower())
            else:
                logging.info('Shelly: <set_light> not implemented api version!')

def get_light_state(light):
    config = light.protocol_cfg
    logging.debug('Shelly: <get_light_state> invoked! IP=' + config['ip'])

    state = {}
    if (not 'gen' in config) or (config['gen'] == 1):
        data = request_api_v1(config['ip'], 'relay/0')
        state['on'] = data['ison'] if 'ison' in data else False
    elif (config['gen'] == 2) or (config['gen'] == 3):
        data = request_api_v2(config['ip'], 'Switch.GetStatus?id=0')
        state['on'] = data['output'] if 'output' in data else False
    else:
        logging.info('Shelly: <get_light_state> not implemented api version!')

    return state

def request_api_v1(ip, request):
    head = {'Content-type': 'application/json'}
    response = requests.get('http://' + ip + '/' + request, timeout = 5, headers = head)
    return json.loads(response.text) if response.status_code == 200 else {}

def request_api_v2(ip, request):
    head = {'Content-type': 'application/json'}
    response = requests.get('http://' + ip + '/rpc/' + request, timeout = 5, headers = head)
    return json.loads(response.text) if response.status_code == 200 else {}
