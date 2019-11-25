#!/bin/bash

echo -e "\033[32m Updating repository.\033[0m"
opkg update
wait
echo -e "\033[32m Installing dependencies.\033[0m"
opkg install gcc make automake ca-bundle git git-http nano nmap python3 python3-pip python3-setuptools openssl-util curl unzip coap-client
wait
export LC_ALL=C
echo -e "\033[32m Creating directories.\033[0m"
mkdir /opt
mkdir /opt/tmp
mkdir /opt/hue-emulator
echo -e "\033[32m Updating python3-pip.\033[0m"
python3 -m pip install --upgrade pip
wait
echo -e "\033[32m Installing pip dependencies.\033[0m"
pip3 install requests ws4py
wait
cd /opt/tmp
echo -e "\033[32m Downloading diyHue.\033[0m"
git clone https://github.com/diyHue/diyHue.git
wait
echo -e "\033[32m Copying files to directories.\033[0m"
cd /opt/tmp/diyHue/BridgeEmulator
cp HueEmulator3.py ssl_server2_diyhue.c default-config.json updater /opt/hue-emulator/
cp -r web-ui /opt/hue-emulator/
cp -r debug functions protocols web-ui /opt/hue-emulator/
cp -r default-config.json /opt/hue-emulator/config.json
echo -e "\033[32m Copying custom network function for openwrt.\033[0m"
rm -Rf /opt/hue-emulator/functions/network.py
mv /opt/tmp/diyHue/functions/network_OpenWrt.py /opt/hue-emulator/functions/network.py
wait
cp hueemulatorWrt-service /etc/init.d/
echo -e "\033[32m Downloading astral.\033[0m"
wget -q https://github.com/sffjunkie/astral/archive/master.zip -O astral.zip
wait
unzip -q -o astral.zip
wait
cd astral-master/
python3 setup.py install
wait
cd ../
rm -rf astral.zip astral-master/
echo -e "\033[32m Download mbedtls to compile binary entertainment.\033[0m"
wait
cd /opt/hue-emulator
export CC=gcc
wget https://github.com/ARMmbed/mbedtls/archive/1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482.zip
wait
unzip 1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482.zip
wait
cd mbedtls-1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482/
wget https://raw.githubusercontent.com/diyhue/diyHue/master/BridgeEmulator/ssl_server2_diyhue.c
wait
make no_test
wait
gcc -I../mbedtls/include ssl_server2_diyhue.c -o ssl_server2_diyhue -L../mbedtls/library -lmbedtls -lmbedx509 -lmbedcrypto
wait
cp /opt/hue-emulator/mbedtls/ssl_server2_diyhue /opt/hue-emulator/entertain-srv
wait
cd /opt/hue-emulator
rm -Rf /opt/hue-emulator/mbedtls-1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482
wait
arch=`uname -m`
echo -e "\033[32m Compiled binary for: $arch.\033[0m"
echo -e "\033[32m uploading binary $arch to remote server.\033[0m"
curl --upload-file /opt/hue-emulator/entertain-srv https://transfer.sh/entertain-srv
echo -e "\033[32m Download the binary at:\033[0m"
echo -e "\033[32m https://transfer.sh/entertain-srv\033[0m"
rm -Rf /opt/hue-emulator/
rm -Rf /opt/tmp
rm -Rf /opt/
wait
exit 0