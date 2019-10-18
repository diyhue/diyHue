#!/bin/bash

echo -e "\033[32m Deleting folders.\033[0m"
rm -Rf /opt/hue-emulator
echo -e "\033[32m Updating repository.\033[0m"
opkg update
wait
echo -e "\033[32m Installing dependencies.\033[0m"
opkg install ca-bundle git git-http nano nmap python3 python3-pip python3-setuptools openssl-util curl coap-client unzip coreutils-nohup
wait
echo -e "\033[32m Creating directories.\033[0m"
mkdir /opt
mkdir /opt/tmp
mkdir /opt/hue-emulator
echo -e "\033[32m Updating python3-pip.\033[0m"
python3 -m pip install --upgrade pip
wait
echo -e "\033[32m Installing pip dependencies.\033[0m"
python3 -m pip install requests astral pytz ws4py
wait
cd /opt/tmp
echo -e "\033[32m Downloading diyHue.\033[0m"
wget -q https://github.com/juanesf/diyHue/archive/master.zip -O diyHue.zip
echo -e "\033[32m Unzip diyHue.\033[0m"
unzip -q -o  diyHue.zip
wait
echo -e "\033[32m Copying unzip files to directories.\033[0m"
cd /opt/tmp/diyHue-master/BridgeEmulator
cp HueEmulator3.py updater /opt/hue-emulator/
cp default-config.json /opt/hue-emulator/config.json
cp default-config.json /opt/hue-emulator/default-config.json
cp -r web-ui /opt/hue-emulator/
cp -r functions protocols debug /opt/hue-emulator/
cp entertainment-mips /opt/hue-emulator/entertain-srv
rm -Rf /opt/hue-emulator/functions/network.py
mv /opt/hue-emulator/functions/network_OpenWrt.py /opt/hue-emulator/functions/network.py
wait
echo -e "\033[32m Copying startup service.\033[0m"
cp hueemulatorWrt-service /etc/init.d/
echo -e "\033[32m Generating certificate.\033[0m"
mac=`cat /sys/class/net/$(ip route get 8.8.8.8 | sed -n 's/.* dev \([^ ]*\).*/\1/p')/address`
curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/cert.pem
echo -e "\033[32m Changing permissions.\033[0m"
chmod +x /etc/init.d/hueemulatorWrt-service
chmod +x /opt/hue-emulator/HueEmulator3.py
chmod +x /opt/hue-emulator/debug
chmod +x /opt/hue-emulator/protocols
chmod +x /opt/hue-emulator/updater
chmod +x /opt/hue-emulator/web-ui
chmod +x /opt/hue-emulator/functions
chmod +x /opt/hue-emulator/config.json
chmod +x /opt/hue-emulator/default-config.json
chmod +x /opt/hue-emulator/entertain-srv
chmod +x /opt/hue-emulator/functions/network.py
echo -e "\033[32m Enable startup service.\033[0m"
/etc/init.d/hueemulatorWrt-service enable
wait
echo -e "\033[32m modify http port 80 to 82: list listen_http 0.0.0.0:82, list listen_http [::]: 82 and server.port = 82.\033[0m"
echo -e "\033[32m To save the changes you've made, press CTRL + O. To exit nano, press CTRL + X.\033[0m"
sleep 20s
nano /etc/config/uhttpd
wait
nano /etc/lighttpd/lighttpd.conf
echo -e "\033[32m Installation completed.\033[0m"
rm -Rf /opt/tmp
echo -e "\033[32m Restarting...\033[0m"
wait
reboot 03
exit 0
