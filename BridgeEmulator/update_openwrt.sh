#!/bin/bash

# To build entertainment srv from source use:
# export COMPILE_ENTERTAIN_SRV=true

echo -e "\033[32m Disable startup service.\033[0m"
/etc/init.d/hueemulatorWrt-service disable
echo -e "\033[32m Create directory for backup configuration.\033[0m"
mkdir /tmp/diyHue-config
echo -e "\033[32m Copying configuration file.\033[0m"
cp /opt/hue-emulator/config.json /tmp/diyHue-config/config.json.bak
cp /opt/hue-emulator/cert.pem /tmp/diyHue-config/cert.pem.bak
echo -e "\033[32m Deleting directories.\033[0m"
rm -Rf /opt/hue-emulator
rm -Rf /etc/init.d/hueemulatorWrt-service
echo -e "\033[32m Updating python3-pip.\033[0m"
python3 -m pip install --upgrade pip
wait
echo -e "\033[32m Updating pip dependencies.\033[0m"
python3 -m pip install --upgrade requests
wait
python3 -m pip install --upgrade astral
wait
python3 -m pip install --upgrade pytz
wait
python3 -m pip install --upgrade ws4py
wait
echo -e "\033[32m Creating directories.\033[0m"
mkdir /opt
mkdir /opt/tmp
mkdir /opt/hue-emulator
cd /opt/tmp
echo -e "\033[32m Downloading diyHue.\033[0m"
wget -q https://github.com/juanesf/diyHue/archive/master.zip -O diyHue.zip
echo -e "\033[32m Unzip diyHue.\033[0m"
unzip -q -o  diyHue.zip
wait
echo -e "\033[32m Copying unzip files to directories.\033[0m"
cd /opt/tmp/diyHue-master/BridgeEmulator
cp HueEmulator3.py updater /opt/hue-emulator/
cp /tmp/diyHue-config/config.json.bak /opt/hue-emulator/config.json
cp /tmp/diyHue-config/cert.pem.bak /opt/hue-emulator/cert.pem
cp default-config.json /opt/hue-emulator/default-config.json
cp -r web-ui /opt/hue-emulator/
cp -r functions protocols debug /opt/hue-emulator/

if [ "$COMPILE_ENTERTAIN_SRV" = "true" ]
then

	# Build from Source
	opkg update
	wait
	opkg install gcc make automake ca-bundle git git-http nano nmap python3 python3-pip python3-setuptools openssl-util curl unzip coap-client
	wait
	cd /opt/tmp/diyHue*/BridgeEmulator
	mv ssl_server2_diyhue.c /opt/hue-emulator/
	cd /opt/hue-emulator
	wait
	git clone https://github.com/ARMmbed/mbedtls.git
	cp /opt/hue-emulator/ssl_server2_diyhue.c /opt/hue-emulator/mbedtls
	cd /opt/hue-emulator/mbedtls
	git checkout master
	git submodule update --init --recursive
	export CC=gcc && make no_test
	wait
	gcc -I../mbedtls/include ssl_server2_diyhue.c -o ssl_server2_diyhue -L../mbedtls/library -lmbedtls -lmbedx509 -lmbedcrypto
	wait
	cp /opt/hue-emulator/mbedtls/ssl_server2_diyhue /opt/hue-emulator/entertain-srv
	cd /opt/tmp/diyHue-master/BridgeEmulator
	wait
	rm -Rf /opt/hue-emulator/mbedtls

else
	
	# Use Prebuilt Binary
	machine_type=$(uname -m)
	case $machine_type in
		 aarch64)
			  echo -e "\033[32m Copying entertainment-aarch64.\033[0m"
			  cp entertainment-openwrt-aarch64 /opt/hue-emulator/entertain-srv
			  ;;
		 arm*)
			  echo -e "\033[32m Copying entertainment-arm.\033[0m"
			  cp entertainment-openwrt-arm /opt/hue-emulator/entertain-srv
			  ;;
		 x86_64|amd64)
			  echo -e "\033[32m Copying entertainment-x86_64.\033[0m"
			  cp entertainment-openwrt-x86_64 /opt/hue-emulator/entertain-srv
			  ;;
		 i?86)
			  echo -e "\033[32m Copying entertainment-i686.\033[0m"
			  cp entertainment-openwrt-i686 /opt/hue-emulator/entertain-srv
			  ;;
		 *) # Default to MIPS
			  echo -e "\033[32m Copying entertainment-mips.\033[0m"
			  cp entertainment-openwrt-mips /opt/hue-emulator/entertain-srv
			  ;;
	esac
fi

rm -Rf /opt/hue-emulator/functions/network.py
mv /opt/hue-emulator/functions/network_OpenWrt.py /opt/hue-emulator/functions/network.py
wait
echo -e "\033[32m Copying startup service.\033[0m"
cp /opt/tmp/diyHue-master/BridgeEmulator/hueemulatorWrt-service /etc/init.d/
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
echo -e "\033[32m Update completed.\033[0m"
rm -Rf /opt/tmp
echo -e "\033[32m Restarting...\033[0m"
wait
reboot 10
exit 0
