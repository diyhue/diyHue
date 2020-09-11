#!/bin/bash

echo -e "\033[32m Deleting folders.\033[0m"
rm -Rf /opt/hue-emulator
echo -e "\033[32m Updating repository.\033[0m"
opkg update
wait
echo -e "\033[32m Installing dependencies.\033[0m"
opkg install ca-bundle git git-http nano nmap python3 python3-pip python3-setuptools
wait
opkg install curl coap-client unzip coreutils-nohup openssl-util
wait
opkg install python3-requests python3-astral python3-pytz python3-paho-mqtt
wait
echo -e "\033[32m Updating python3-pip.\033[0m"
python3 -m pip install --upgrade pip
wait
echo -e "\033[32m Installing pip dependencies.\033[0m"
python3 -m pip install ws4py
wait
echo -e "\033[32m Creating directories.\033[0m"
mkdir /opt
mkdir /opt/tmp
mkdir /opt/hue-emulator
cd /opt/tmp
echo -e "\033[32m Downloading diyHue.\033[0m"
wget -q https://github.com/diyhue/diyHue/archive/master.zip -O diyHue.zip
echo -e "\033[32m Unzip diyHue.\033[0m"
unzip -q -o  diyHue.zip
wait
echo -e "\033[32m Copying unzip files to directories.\033[0m"
cd /opt/tmp/diyHue-master/BridgeEmulator
cp HueEmulator3.py updater /opt/hue-emulator/
cp default-config.json /opt/hue-emulator/config.json
cp default-config.json /opt/hue-emulator/default-config.json
cp -r configManager debug devices functions logManager protocols responseBuilder web-ui webServer /opt/hue-emulator/
echo -e "\033[32m Detecting processor architecture.\033[0m"
wait
arch=`uname -m`
wait
echo -e "\033[32m Architecture detected: $arch\033[0m"
echo -e "\033[32m Copying binary $arch for Openwrt.\033[0m"
cp ../Installers/OpenWrt/entertainment-openwrt-$arch /opt/hue-emulator/entertain-srv
echo -e "\033[32m Copying custom network function for openwrt.\033[0m"
rm -Rf /opt/hue-emulator/functions/network.py
mv ../Installers/OpenWrt/network_OpenWrt.py /opt/hue-emulator/functions/network.py
wait
echo -e "\033[32m Copying startup service.\033[0m"
cp ../Installers/OpenWrt/hueemulatorWrt-service /etc/init.d/
echo -e "\033[32m Generating certificate.\033[0m"
#mac=`cat /sys/class/net/$(ip route get 8.8.8.8 | sed -n 's/.* dev \([^ ]*\).*/\1/p')/address`
mac=`cat /sys/class/net/br-lan/address`
curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/cert.pem
echo -e "\033[32m Changing permissions.\033[0m"
chmod +x /etc/init.d/hueemulatorWrt-service
chmod +x /opt/hue-emulator/HueEmulator3.py
chmod +x /opt/hue-emulator/debug
chmod +x /opt/hue-emulator/devics
chmod +x /opt/hue-emulator/functions
chmod +x /opt/hue-emulator/logManager
chmod +x /opt/hue-emulator/protocols
chmod +x /opt/hue-emulator/responseBuilder
chmod +x /opt/hue-emulator/webServer
chmod +x /opt/hue-emulator/updater
chmod +x /opt/hue-emulator/web-ui
chmod +x /opt/hue-emulator/config.json
chmod +x /opt/hue-emulator/default-config.json
chmod +x /opt/hue-emulator/entertain-srv
chmod +x /opt/hue-emulator/functions/network.py
chmod +x /opt/hue-emulator
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
reboot 10
exit 0
