#!/bin/bash
mac=`cat /sys/class/net/$(ip addr show | awk '/inet.*brd/{print $NF}')/address`
arch=`uname -m`

### test is server for certificate generation is reachable

if ! nc -z mariusmotea.go.ro 9002 2>/dev/null; then
        echo -e "\033[31m ERROR!! Certificate generation service is down. Please retry in one hour.\033[0m"
        exit 1
fi

if [ $(uname -m) != "armv7l" -a $(uname -m) != "armv6l" ]; then
        echo -e "\033[33m WARNING! Only arm plafrorm support Tradfri Gateway proxy.\033[0m"
fi

cd /tmp

### installing dependencies
echo -e "\033[36m Installing dependencies.\033[0m"
apt install -y unzip nmap python3 python3-requests python3-ws4py python3-setuptools nginx

echo -e "\033[36m Installing Python Astral.\033[0m"
### installing astral library for sunrise/sunset routines
wget https://github.com/sffjunkie/astral/archive/master.zip -O astral.zip
unzip -q astral.zip
cd astral-master/
python3 setup.py install
cd ../
rm -rf astral.zip astral-master/

echo -e "\033[36m Installing Hue Emulator.\033[0m"
### installing hue emulator
wget https://github.com/mariusmotea/diyHue/archive/master.zip -O diyHue.zip
unzip -q diyHue.zip
cd diyHue-master/BridgeEmulator/

if [ -d "/opt/hue-emulator" ]; then
        echo -e "\033[33m Existing installation found, performing upgrade.\033[0m"
        cp /opt/hue-emulator/config.json /tmp
        rm -rf /opt/hue-emulator
        mkdir /opt/hue-emulator
        mv /tmp/config.json /opt/hue-emulator
        cp -r web-ui functions HueEmulator3.py coap-client-linux /opt/hue-emulator/
        cp entertainment-`uname -m` /opt/hue-emulator/entertainment-srv

else
        mkdir /opt/hue-emulator
        cp -r web-ui functions HueEmulator3.py coap-client-linux config.json /opt/hue-emulator/
        cp entertainment-`uname -m` /opt/hue-emulator/entertainment-srv
fi
cp hue-emulator.service /lib/systemd/system/
cp nginx/nginx.conf nginx/apiv1.conf /etc/nginx/
cd ../../
rm -rf diyHue.zip diyHue-master
curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/public.crt
curl "http://mariusmotea.go.ro:9002/gencert?priv=true" > /opt/hue-emulator/private.key
systemctl restart nginx
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service 
systemctl start hue-emulator.service

echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
