#!/bin/bash
mac=`cat /sys/class/net/$(ip addr show | awk '/inet.*brd/{print $NF}')/address`
arch=`uname -m`

cd /tmp

### installing dependencies
echo -e "\033[36m Installing dependencies.\033[0m"
apt install -y unzip nmap python3 python3-requests python3-ws4py python3-setuptools nginx

### installing astral library for sunrise/sunset routines
echo -e "\033[36m Installing Python Astral.\033[0m"
wget -q https://github.com/sffjunkie/astral/archive/master.zip -O astral.zip
unzip -q -o astral.zip
cd astral-master/
python3 setup.py install
cd ../
rm -rf astral.zip astral-master/

### installing hue emulator
echo -e "\033[36m Installing Hue Emulator.\033[0m"
wget -q https://github.com/mariusmotea/diyHue/archive/master.zip -O diyHue.zip
unzip -q -o  diyHue.zip
cd diyHue-master/BridgeEmulator/

if [ -d "/opt/hue-emulator" ]; then
        if [ -f "/opt/hue-emulator/public.crt" ]; then
                cp /opt/hue-emulator/public.crt /opt/hue-emulator/private.key /tmp
        else
		### test is server for certificate generation is reachable
                if ! nc -z mariusmotea.go.ro 9002 2>/dev/null; then
                        echo -e "\033[31m ERROR!! Certificate generation service is down. Please try again later.\033[0m"
                        exit 1
                fi
                curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /tmp/public.crt
                curl "http://mariusmotea.go.ro:9002/gencert?priv=true" > /tmp/private.key
        fi
	systemctl stop hue-emulator.service
        echo -e "\033[33m Existing installation found, performing upgrade.\033[0m"
        cp /opt/hue-emulator/config.json /tmp
        rm -rf /opt/hue-emulator
        mkdir /opt/hue-emulator
        mv /tmp/config.json /opt/hue-emulator
        mv /tmp/private.key /tmp/public.crt /opt/hue-emulator

else
        if nc -z 127.0.0.1 80 2>/dev/null; then
                echo -e "\033[31m ERROR!! Port 80 already in use. Close the application that use this port and try again.\033[0m"
                exit 1
        fi
        if nc -z 127.0.0.1 443 2>/dev/null; then
                echo -e "\033[31m ERROR!! Port 443 already in use. Close the application that use this port and try again.\033[0m"
                exit 1
        fi
        mkdir /opt/hue-emulator
        cp config.json /opt/hue-emulator/
        curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/public.crt
        curl "http://mariusmotea.go.ro:9002/gencert?priv=true" > /opt/hue-emulator/private.key
fi
cp -r web-ui functions HueEmulator3.py /opt/hue-emulator/
if [ $(uname -m) = "x86_64" ]; then
	cp entertainment-x86_64 /opt/hue-emulator/entertainment-srv
	cp coap-client-x86_64 /opt/hue-emulator/coap-client-linux
else
	cp entertainment-arm /opt/hue-emulator/entertainment-srv
        cp coap-client-arm /opt/hue-emulator/coap-client-linux
fi
cp hue-emulator.service /lib/systemd/system/
cp nginx/nginx.conf nginx/apiv1.conf /etc/nginx/
cd ../../
rm -rf diyHue.zip diyHue-master
systemctl restart nginx
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service 
systemctl start hue-emulator.service

echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
