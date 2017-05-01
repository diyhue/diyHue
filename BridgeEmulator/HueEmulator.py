#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from time import strftime, sleep
from datetime import datetime, timedelta
from pprint import pprint
from subprocess import check_output
import json, socket, hashlib, urllib2, struct, random
from threading import Thread
from collections import defaultdict
from uuid import getnode as get_mac
from urlparse import urlparse, parse_qs

mac = '%012x' % get_mac()

run_service = True

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def ssdp_search():
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900
    MSEARCH_Interval = 2
    multicast_group_c = SSDP_ADDR
    multicast_group_s = (SSDP_ADDR, SSDP_PORT)
    server_address = ('', SSDP_PORT)
    Response_message = 'HTTP/1.1 200 OK\r\nHOST: 239.255.255.250:1900\r\nEXT:CACHE-CONTROL: max-age=100\r\nLOCATION: http://' + get_ip_address() + ':80/description.xml\r\nSERVER: Linux/3.14.0 UPnP/1.0 IpBridge/1.16.0\r\nhue-bridgeid: ' + mac.upper() + '\r\nST: urn:schemas-upnp-org:device:basic:1\r\nUSN: uuid:2f402f80-da50-11e1-9b23-' + mac
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)

    group = socket.inet_aton(multicast_group_c)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print("starting ssdp...")

    while run_service:
              data, address = sock.recvfrom(1024)
              if data[0:19]== 'M-SEARCH * HTTP/1.1':
                   if data.find("ssdp:all") != -1:
                          sleep(random.randrange(0, 3))
                          print("Sending M Search response")
                          sock.sendto(Response_message, address)
              sleep(1)

def scheduler_processor():
    while run_service:
        for schedule in bridge_config["schedules"].iterkeys():
            if bridge_config["schedules"][schedule]["status"] == "enabled":
                if bridge_config["schedules"][schedule]["localtime"].startswith("W"):
                    pices = bridge_config["schedules"][schedule]["localtime"].split('/T')
                    if int(pices[0][1:]) & (1 << 6 - datetime.today().weekday()):
                        if pices[1] == datetime.now().strftime("%H:%M:%S"):
                            print("execute schedule: " + schedule)
                            sendActionRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]))
                elif bridge_config["schedules"][schedule]["localtime"].startswith("PT"):
                    if bridge_config["schedules"][schedule]["starttime"] == datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"):
                        print("execute timmer: " + schedule)
                        sendActionRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]))
                        bridge_config["schedules"][schedule]["status"] = "disabled"
                else:
                    if bridge_config["schedules"][schedule]["localtime"] == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                        print("execute schedule: " + schedule)
                        sendActionRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]))
        sleep(1)
        if (datetime.now().strftime("%M:%S") == "00:00"): #auto save configuration every hour
            save_config()

def rules_processor():
    for rule in bridge_config["rules"].iterkeys():
        if bridge_config["rules"][rule]["status"] == "enabled":
            execute = True
            for condition in bridge_config["rules"][rule]["conditions"]:
                url_pices = condition["address"].split('/')
                if condition["operator"] == "eq":
                    if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) == int(condition["value"]):
                        execute = False
                elif condition["operator"] == "gt":
                    if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) > int(condition["value"]):
                        execute = False
                elif condition["operator"] == "lt":
                    if int(not bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) < int(condition["value"]):
                        execute = False
                elif condition["operator"] == "dx":
                    if not bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]] == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                        execute = False
            if execute:
                print("rule " + rule + " is triggered")
                for action in bridge_config["rules"][rule]["actions"]:
                    Thread(target=sendActionRequest, args=["/api/" + bridge_config["rules"][rule]["owner"] + action["address"], action["method"], json.dumps(action["body"])]).start()


def sendActionRequest(url, method, data):
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    request = urllib2.Request("http://127.0.0.1" + url, data=data)
    request.add_header("Content-Type",'application/json')
    request.get_method = lambda: method
    url = opener.open(request)



def sendLightRequest(light, data):
    url = "http://" + lights_address[light]["ip"] + "/set?light=" + str(lights_address[light]["light_nr"]);
    for key, value in data.iteritems():
        if key == "xy":
            url += "&x=" + str(value[0]) + "&y=" + str(value[1])
        else:
            url += "&" + key + "=" + str(value)
    try:
        urllib2.urlopen(url, timeout = 3).read()
    except:
        bridge_config["lights"][light]["state"]["reachable"] = False
    else:
        bridge_config["lights"][light]["state"]["reachable"] = True
    print("LightRequest: " + url)

class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value

bridge_config = defaultdict(lambda:defaultdict(str))#Vividict()
new_lights = {}
lights_address = {}

try:
    with open('/home/pi/config.json', 'r') as fp:
        bridge_config = json.load(fp)
        print("config loaded")
except Exception:
    print("config file was not loaded")

try:
    with open('/home/pi/lights_address.json', 'r') as fp:
        lights_address = json.load(fp)
        print("lights address loaded")
except Exception:
    print("lights adress file was not loaded")

bridge_config["config"]["ipaddress"] = get_ip_address()
bridge_config["config"]["mac"] = mac[0] + mac[1] + ":" + mac[2] + mac[3] + ":" + mac[4] + mac[5] + ":" + mac[6] + mac[7] + ":" + mac[8] + mac[9] + ":" + mac[10] + mac[11]
bridge_config["config"]["bridgeid"] = mac.upper()


def save_config():
    with open('/home/pi/config.json', 'w') as fp:
        json.dump(bridge_config, fp, sort_keys=True, indent=4, separators=(',', ': '))
    with open('/home/pi/lights_address.json', 'w') as fp:
        json.dump(lights_address, fp, sort_keys=True, indent=4, separators=(',', ': '))

def update_group_stats(light):
    for group in bridge_config["groups"]:
        if light in bridge_config["groups"][group]["lights"]:
            for key, value in bridge_config["lights"][light]["state"].iteritems():
                if key not in ["on", "reachable"]:
                    bridge_config["groups"][group]["action"][key] = value
            any_on = False
            all_on = True
            bri = 0
            for group_light in bridge_config["groups"][group]["lights"]:
                if bridge_config["lights"][light]["state"]["on"] == True:
                    any_on = True
                else:
                    all_on = False
                bri += bridge_config["lights"][light]["state"]["bri"]
            avg_bri = bri / len(bridge_config["groups"][group]["lights"])
            bridge_config["groups"][group]["state"] = {"any_on": any_on, "all_on": all_on, "bri": avg_bri, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}


def description():
    return """<root xmlns=\"urn:schemas-upnp-org:device-1-0\">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<URLBase>http://""" + get_ip_address() + """:80/</URLBase>
<device>
<deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>
<friendlyName>Philips hue</friendlyName>
<manufacturer>Royal Philips Electronics</manufacturer>
<manufacturerURL>http://www.philips.com</manufacturerURL>
<modelDescription>Philips hue Personal Wireless Lighting</modelDescription>
<modelName>Philips hue bridge 2015</modelName>
<modelNumber>BSB002</modelNumber>
<modelURL>http://www.meethue.com</modelURL>
<serialNumber>""" + mac.upper() + """</serialNumber>
<UDN>MYUUID</UDN>
<presentationURL>index.html</presentationURL>
<iconList>
<icon>
<mimetype>image/png</mimetype>
<height>48</height>
<width>48</width>
<depth>24</depth>
<url>hue_logo_0.png</url>
</icon>
<icon>
<mimetype>image/png</mimetype>
<height>120</height>
<width>120</width>
<depth>24</depth>
<url>hue_logo_3.png</url>
</icon>
</iconList>
</device>
</root>"""

class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        if self.path == '/description.xml':
            self.wfile.write(description())
        elif self.path.startswith("/switch"):
            get_parameters = parse_qs(urlparse(self.path).query)
            pprint(get_parameters)
            if "devicetype" in get_parameters:
                sensor_is_new = True
                for sensor in bridge_config["sensors"]:
                    if get_parameters["mac"][0] == bridge_config["sensors"][sensor]["uniqueid"]:
                        sensor_is_new = False
                if sensor_is_new:
                    print("registering new sensor " + get_parameters["devicetype"][0])
                    i = 1
                    while (str(i)) in bridge_config["sensors"]:
                        i += 1
                    bridge_config["sensors"][str(i)] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if get_parameters["devicetype"][0] == "ZLLSwitch" else "Tap Switch", "type": get_parameters["devicetype"][0], "modelid": "RWL021" if get_parameters["devicetype"][0] == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if get_parameters["devicetype"][0] == "ZLLSwitch" else "", "uniqueid": get_parameters["mac"][0]}
            else:
                for sensor in bridge_config["sensors"]:
                    if get_parameters["mac"][0] == bridge_config["sensors"][sensor]["uniqueid"]:
                        bridge_config["sensors"][sensor]["state"].update({"buttonevent": get_parameters["button"][0], "lastupdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        rules_processor()
        else:
            url_pices = self.path.split('/')
            pprint(url_pices)
            if url_pices[2] in bridge_config["config"]["whitelist"]:
                bridge_config["config"]["UTC"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["localtime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                if len(url_pices) == 3:
                    self.wfile.write(json.dumps(bridge_config))
                elif len(url_pices) == 4:
                    self.wfile.write(json.dumps(bridge_config[url_pices[3]]))
                elif len(url_pices) == 5:
                    if url_pices[4] == "new": #return new lights and sensors only
                        new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        self.wfile.write(json.dumps(new_lights))
                        new_lights.clear()
                    else:
                        self.wfile.write(json.dumps(bridge_config[url_pices[3]][url_pices[4]]))
                elif len(url_pices) == 6:
                    self.wfile.write(json.dumps(bridge_config[url_pices[3]][url_pices[4]][url_pices[5]]))
            elif (url_pices[2] == "nouser" or url_pices[2] == "config") :
                self.wfile.write(json.dumps({"name": bridge_config["config"]["name"],"datastoreversion": 59, "swversion": bridge_config["config"]["swversion"], "apiversion": bridge_config["config"]["apiversion"], "mac": bridge_config["config"]["mac"], "bridgeid": bridge_config["config"]["bridgeid"], "factorynew": False, "modelid": bridge_config["config"]["modelid"]}))
            else:
                self.wfile.write(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}]))


    def do_POST(self):
        self._set_headers()
        print "in post method"
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        post_dictionary = json.loads(self.data_string)
        url_pices = self.path.split('/')
        print(self.path)
        print(self.data_string)
        if len(url_pices) == 4: #data was posted to a location
            if url_pices[2] in bridge_config["config"]["whitelist"]:
                if ((url_pices[3] == "lights" or url_pices[3] == "sensors") and not bool(post_dictionary)):
                    #if was a request to scan for lights of sensors
                    print(json.dumps([{"success": {"/" + url_pices[3]: "Searching for new devices"}}], sort_keys=True, indent=4, separators=(',', ': ')))
                    #return all host that listen on port 80
                    device_ips = check_output("nmap  " + get_ip_address() + "/24 -p80 --open -n | grep report | cut -d ' ' -f5", shell=True).split("\n")
                    del device_ips[-1] #delete last empty element in list
                    for ip in device_ips:
                        if ip != get_ip_address():
                            try:
                                f = urllib2.urlopen("http://" + ip + "/detect")
                                device_data = json.loads(f.read())
                                if device_data.keys()[0] == "hue":
                                    print(ip + " is a hue " + device_data['hue'])
                                    device_exist = False
                                    for light in bridge_config["lights"].iterkeys():
                                        if bridge_config["lights"][light]["uniqueid"].startswith( device_data["mac"] ):
                                            device_exist = True
                                            lights_address[light]["ip"] = ip
                                    if not device_exist:
                                        print("is a new device")
                                        for x in xrange(1, int(device_data["lights"]) + 1):
                                            i = 1
                                            while (str(i)) in bridge_config[url_pices[3]]:
                                                i += 1
                                            bridge_config["lights"][str(i)] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": "Hue " + device_data["type"] + " " + device_data["hue"] + " " + str(x), "uniqueid": device_data["mac"] + "-" + str(x), "modelid": "LST001" if device_data["hue"] == "strip" else "LCT001", "swversion": "66009461"}
                                            new_lights.update({str(i): {"name": "Hue " + device_data["type"] + " " + device_data["hue"] + " " + str(x)}})
                                            lights_address[str(i)] = {"ip": ip, "light_nr": x}
                            except Exception, e:
                                print(ip + " is unknow device " + str(e))
                    self.wfile.write(json.dumps([{"success": {"/" + url_pices[3]: "Searching for new devices"}}], sort_keys=True, indent=4, separators=(',', ': ')))
                else: #create object
                    # find the first unused if for new objecy
                    i = 1
                    while (str(i)) in bridge_config[url_pices[3]]:
                        i += 1
                    if url_pices[3] == "scenes":
                        post_dictionary.update({"lightstates": {}, "version": 2, "picture": "", "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                    elif url_pices[3] == "groups":
                        post_dictionary.update({"action": {"on": False}, "state": {"any_on": False, "all_on": False}})
                    elif url_pices[3] == "schedules":
                        post_dictionary.update({"created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        if post_dictionary["localtime"].startswith("PT"):
                            timmer = post_dictionary["localtime"][2:]
                            (h, m, s) = timmer.split(':')
                            d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                            post_dictionary.update({"starttime": (datetime.utcnow() + d).strftime("%Y-%m-%dT%H:%M:%S")})
                        if not "status" in post_dictionary:
                            post_dictionary.update({"status": "enabled"})
                    elif url_pices[3] == "rules":
                        post_dictionary.update({"owner": url_pices[2]})
                        if not "status" in post_dictionary:
                            post_dictionary.update({"status": "enabled"})
                    bridge_config[url_pices[3]][str(i)] = post_dictionary
                    print(json.dumps([{"success": {"id": str(i)}}], sort_keys=True, indent=4, separators=(',', ': ')))
                    self.wfile.write(json.dumps([{"success": {"id": str(i)}}], sort_keys=True, indent=4, separators=(',', ': ')))
            else:
                self.wfile.write(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))
                print(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))
        elif len(url_pices) == 3: #this must be a new device registration
                #create new user hash
                s = hashlib.new('ripemd160', post_dictionary["devicetype"][0]        ).digest()
                username = s.encode('hex')
                bridge_config["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": post_dictionary["devicetype"][0]}
                self.wfile.write(json.dumps([{"success": {"username": username}}], sort_keys=True, indent=4, separators=(',', ': ')))
                print(json.dumps([{"success": {"username": username}}], sort_keys=True, indent=4, separators=(',', ': ')))
        self.end_headers()
        save_config()

    def do_PUT(self):
        self._set_headers()
        print "in PUT method"
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        put_dictionary = json.loads(self.data_string)
        url_pices = self.path.split('/')
        if url_pices[2] in bridge_config["config"]["whitelist"]:
            print(len(url_pices))
            if len(url_pices) == 4:
                bridge_config[url_pices[3]].update(put_dictionary)
                response_location = "/" + url_pices[3] + "/"
            if len(url_pices) == 5:
                if url_pices[3] == "schedules":
                    if "status" in put_dictionary and put_dictionary["status"] == "enabled" and bridge_config["schedules"][url_pices[4]]["localtime"].startswith("PT"):
                        if "localtime" in put_dictionary:
                            timmer = put_dictionary["localtime"][2:]
                        else:
                            timmer = bridge_config["schedules"][url_pices[4]]["localtime"][2:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        put_dictionary.update({"starttime": (datetime.utcnow() + d).strftime("%Y-%m-%dT%H:%M:%S")})
                bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/"
            if len(url_pices) == 6:
                if url_pices[3] == "groups": #state is applied to a group
                    if "scene" in put_dictionary: #if group is 0 and there is a scene applied
                        for light in bridge_config["scenes"][put_dictionary["scene"]]["lights"]:
                            sendLightRequest(light, bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light])
                            bridge_config["lights"][light]["state"].update(bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light])
                            if "xy" in bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light]: #color mode must be setup by bridge
                                bridge_config["lights"][light]["state"]["colormode"] = "xy"
                            else:
                                bridge_config["lights"][light]["state"]["colormode"] = "ct"
                    elif "bri_inc" in put_dictionary:
                        bridge_config["groups"][url_pices[4]]["action"]["bri"] += int(put_dictionary["bri_inc"])
                        if bridge_config["groups"][url_pices[4]]["action"]["bri"] > 254:
                            bridge_config["groups"][url_pices[4]]["action"]["bri"] = 254
                        elif bridge_config["groups"][url_pices[4]]["action"]["bri"] < 1:
                            bridge_config["groups"][url_pices[4]]["action"]["bri"] = 1
                        del put_dictionary["bri_inc"]
                        put_dictionary.update({"bri": bridge_config["groups"][url_pices[4]]["action"]["bri"]})
                        for light in bridge_config["groups"][url_pices[4]]["lights"]:
                            sendLightRequest(light, put_dictionary)
                    elif url_pices[4] == "0":
                        for light in bridge_config["lights"].iterkeys():
                            bridge_config["lights"][light]["state"].update(put_dictionary)
                            sendLightRequest(light, put_dictionary)
                            for group in bridge_config["groups"].iterkeys():
                                bridge_config["groups"][group][url_pices[5]].update(put_dictionary)
                                if put_dictionary["on"]:
                                    bridge_config["groups"][group]["state"]["any_on"] = put_dictionary["on"]
                                    bridge_config["groups"][group]["state"]["all_on"] = put_dictionary["on"]
                    else: # the state is applied to particular group (url_pices[4])
                        for light in bridge_config["groups"][url_pices[4]]["lights"]:
                                bridge_config["lights"][light]["state"].update(put_dictionary)
                                sendLightRequest(light, put_dictionary)
                elif url_pices[3] == "lights": #state is applied to a light
                    sendLightRequest(url_pices[4], put_dictionary)
                    for key in put_dictionary.iterkeys():
                        if key in ["ct", "xy", "hue"]: #colormode must be set by bridge
                            bridge_config["lights"][url_pices[4]]["state"]["colormode"] = key
                    update_group_stats(url_pices[4])
                if not url_pices[4] == "0": #group 0 is virtual, must not be saved in bridge configuration
                    try:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]].update(put_dictionary)
                    except KeyError:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]] = put_dictionary
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/" + url_pices[5] + "/"
            if len(url_pices) == 7:
                print("are 7")
                try:
                    bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]].update(put_dictionary)
                except KeyError:
                    bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]] = put_dictionary
                bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]] = put_dictionary
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/" + url_pices[5] + "/" + url_pices[6] + "/"
            response_dictionary = []
            for key, value in put_dictionary.iteritems():
                response_dictionary.append({"success":{response_location + key: value}})
            self.wfile.write(json.dumps(response_dictionary,sort_keys=True, indent=4, separators=(',', ': ')))
            print(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
        else:
            self.wfile.write(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))

    def do_DELETE(self):
        self._set_headers()
        url_pices = self.path.split('/')
        if url_pices[2] in bridge_config["config"]["whitelist"]:
            del bridge_config[url_pices[3]][url_pices[4]]
            self.wfile.write(json.dumps([{"success": "/" + url_pices[3] + "/" + url_pices[4] + " deleted."}]))

def run(server_class=HTTPServer, handler_class=S):
    server_address = ('', 80)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd...'
    httpd.serve_forever()

if __name__ == "__main__":
    try:
        Thread(target=ssdp_search).start()
        Thread(target=scheduler_processor).start()
        run()
    except:
        print("server stopped")
    finally:
        run_service = False
        save_config()
        print 'config saved'
