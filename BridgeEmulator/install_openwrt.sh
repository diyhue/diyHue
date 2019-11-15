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
echo -e "\033[32m Detecting processor architecture.\033[0m"
wait
arch=`uname -m`
wait
echo -e "\033[32m Architecture detected: $arch\033[0m"
echo -e "\033[32m Copying binary $arch for Openwrt.\033[0m"
cp entertainment-openwrt-$arch /opt/hue-emulator/entertain-srv
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
echo -e "\033[32m Creating certificate.\033[0m"
#mac=`cat /sys/class/net/$(ip route get 8.8.8.8 | sed -n 's/.* dev \([^ ]*\).*/\1/p')/address`
mac=`cat /sys/class/net/br-lan/address`
curl https://raw.githubusercontent.com/mariusmotea/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf -o openssl.conf
wait
serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
openssl req -new -days 3650 -config openssl.conf -nodes -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial
wait
touch /opt/hue-emulator/cert.pem
cat private.key > /opt/hue-emulator/cert.pem
cat public.crt >> /opt/hue-emulator/cert.pem
rm private.key public.crt
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
chmod +x /opt/hue-emulator
echo -e "\033[32m Enable startup service.\033[0m"
/etc/init.d/hueemulatorWrt-service enable
wait
echo -e "\033[32m Installation completed. run: nano /etc/config/uhttpd and mod htpp port 80 for 82, run: nano /etc/lighttpd/lighttpd.conf and mod server.port = 80 for 82. For save changes ctrl +x, y, and enter..\033[0m"
sleep 15s
nano /etc/config/uhttpd
wait
nano /etc/lighttpd/lighttpd.conf
echo -e "\033[32m Installation completed.\033[0m"
wait
reboot 10
exit 0