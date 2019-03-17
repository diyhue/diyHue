#!/bin/bash

opkg update
wait
opkg install ca-bundle git git-http nano nmap python3 python3-pip python3-setuptools openssl-util curl coap-client unzip coreutils-nohup
wait
mkdir /opt
mkdir /opt/tmp
mkdir /opt/hue-emulator
pip3 install --upgrade pip
wait
pip3 install requests astral pytz
wait
cd /opt/tmp
wget -q https://github.com/diyhue/diyHue/archive/master.zip -O diyHue.zip
unzip -q -o  diyHue.zip
wait
cd /opt/tmp/diyHue-master/BridgeEmulator
cp HueEmulator3.py config.json updater /opt/hue-emulator/
cp -r web-ui /opt/hue-emulator/
cp -r functions protocols debug /opt/hue-emulator/
cp entertainment-mips /opt/hue-emulator/entertainment-srv
rm -Rf /opt/hue-emulator/functions/network.py
mv /opt/hue-emulator/functions/network_OpenWrt.py /opt/hue-emulator/functions/network.py
wait
cp hueemulatorWrt-service /etc/init.d/

mac=`cat /sys/class/net/$(ip route get 8.8.8.8 | sed -n 's/.* dev \([^ ]*\).*/\1/p')/address`
curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/cert.pem

chmod +x /etc/init.d/hueemulatorWrt-service
chmod +x /opt/hue-emulator/HueEmulator3.py
chmod +x /opt/hue-emulator/debug
chmod +x /opt/hue-emulator/protocols
chmod +x /opt/hue-emulator/updater
chmod +x /opt/hue-emulator/web-ui
chmod +x /opt/hue-emulator/functions
chmod +x /opt/hue-emulator/config.json
chmod +x /opt/hue-emulator/entertainment-srv
chmod +x /opt/hue-emulator/functions/network.py
/etc/init.d/hueemulatorWrt-service enable
wait
echo -e "\033[32m Installation completed. run: nano /etc/config/uhttpd and mod htpp port 80 for 82, run: nano /etc/lighttpd/lighttpd.conf and mod server.port = 80 for 82. For save changes ctrl +x, y, and enter..\033[0m"
sleep 20s
nano /etc/config/uhttpd
wait
nano /etc/lighttpd/lighttpd.conf
echo -e "\033[32m Installation completed.\033[0m"
rm -Rf /opt/tmp
wait
exit 0
