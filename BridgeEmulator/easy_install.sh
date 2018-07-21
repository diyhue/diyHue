#!/bin/bash
mac=`cat /sys/class/net/$(ip addr show | awk '/inet.*brd/{print $NF}')/address`
apt install -y git nmap python3 python3-requests python3-ws4py nginx
cd /tmp
git clone https://github.com/mariusmotea/diyHue.git
mkdir /opt/hue-emulator
cd diyHue/BridgeEmulator
cp -r web-ui functions HueEmulator3.py coap-client-linux config.json /opt/hue-emulator/
cp entertainment-`uname -m` /opt/hue-emulator/entertainment-srv
cp hue-emulator.service /lib/systemd/system/
cp nginx/nginx.conf nginx/apiv1.conf /etc/nginx/
curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/public.crt
curl "http://mariusmotea.go.ro:9002/gencert?priv=true" > /opt/hue-emulator/private.key
systemctl restart nginx
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service 
systemctl start hue-emulator.service
echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
