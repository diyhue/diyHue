#!/usr/bin/env bash
mac=`cat /sys/class/net/$(ip route get 8.8.8.8 | sed -n 's/.* dev \([^ ]*\).*/\1/p')/address`
arch=`uname -m`

cd /tmp

### installing dependencies
echo -e "\033[36m Installing dependencies.\033[0m"
if type apt &> /dev/null; then
	# Debian-based distro
	apt-get install -y unzip nmap python3 python3-requests python3-ws4py python3-setuptools
elif type pacman &> /dev/null; then
	# Arch linux
	pacman -Syq --noconfirm || exit 1
	pacman -Sq --noconfirm unzip nmap python3 python-pip gnu-netcat || exit 1
else
	# Or assume that packages are already installed (possibly with user confirmation)?
	# Or check them?
	echo -e "\033[31mUnable to detect package manager, aborting\033[0m"
	exit 1
fi

### installing astral library for sunrise/sunset routines
echo -e "\033[36m Installing Python Astral.\033[0m"
curl -sL https://github.com/sffjunkie/astral/archive/master.zip -o astral.zip
unzip -qo astral.zip
cd astral-master/
python3 setup.py install
cd ../
rm -rf astral.zip astral-master/

### installing hue emulator
echo -e "\033[36m Installing Hue Emulator.\033[0m"
curl -sL https://github.com/diyhue/diyHue/archive/master.zip -o diyHue.zip
unzip -qo diyHue.zip
cd diyHue-master/BridgeEmulator/

if [ -d "/opt/hue-emulator" ]; then
        if [ -f "/opt/hue-emulator/public.crt" ]; then
		echo -e "\033[31m WARNING!! Nginx is not necessary anymore, it will be stopped.\033[0m"
        	systemctl stop nginx
		systemctl disable nginx
		cp /opt/hue-emulator/private.key /tmp/cert.pem
                cat /opt/hue-emulator/public.crt >> /tmp/cert.pem
	elif [ -f "/opt/hue-emulator/cert.pem" ]; then
		cp /opt/hue-emulator/cert.pem /tmp/cert.pem
        else
		curl https://raw.githubusercontent.com/diyhue/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf -o openssl.conf
		serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
		dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
		openssl req -new -days 3650 -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial
		if [ $? -ne 0 ] ; then
			echo -e "\033[31m ERROR!! Local certificate generation failed! Attempting remote server generation\033[0m"
			### test is server for certificate generation is reachable
			if ! nc -z mariusmotea.go.ro 9002 2>/dev/null; then
				echo -e "\033[31m ERROR!! Certificate generation service is down. Please try again later.\033[0m"
				exit 1
			fi
			curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /tmp/cert.pem
		else
			touch /tmp/cert.pem
			cat private.key > /tmp/cert.pem
			cat public.crt >> /tmp/cert.pem
			rm private.key public.crt
		fi
        fi

	systemctl stop hue-emulator.service
        echo -e "\033[33m Existing installation found, performing upgrade.\033[0m"
        cp /opt/hue-emulator/config.json /tmp
        rm -rf /opt/hue-emulator
        mkdir /opt/hue-emulator
        mv /tmp/config.json /opt/hue-emulator
        mv /tmp/cert.pem /opt/hue-emulator

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
        cp default-config.json /opt/hue-emulator/

	curl https://raw.githubusercontent.com/diyhue/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf -o openssl.conf
	serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
	dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
	openssl req -new -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial -days 3650
	if [ $? -ne 0 ] ; then
		echo -e "\033[31m ERROR!! Local certificate generation failed! Attempting remote server generation\033[0m"
		### test is server for certificate generation is reachable
		if ! nc -z mariusmotea.go.ro 9002 2>/dev/null; then
			echo -e "\033[31m ERROR!! Certificate generation service is down. Please try again later.\033[0m"
			exit 1
		fi
		curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/cert.pem
	else
		touch /opt/hue-emulator/cert.pem
		cat private.key > /opt/hue-emulator/cert.pem
		cat public.crt >> /opt/hue-emulator/cert.pem
		rm private.key public.crt
	fi
fi
cp -r web-ui functions protocols HueEmulator3.py check_updates.sh debug/clip.html /opt/hue-emulator/

# Install correct binaries
case $arch in
    x86_64|i686|aarch64)
        cp entertainment-$arch /opt/hue-emulator/entertainment-srv
        cp coap-client-$arch /opt/hue-emulator/coap-client-linux
       ;;
    arm64)
        cp entertainment-aarch64 /opt/hue-emulator/entertainment-srv
        cp coap-client-aarch64 /opt/hue-emulator/coap-client-linux
       ;;
    armv*)
        cp entertainment-arm /opt/hue-emulator/entertainment-srv
        cp coap-client-arm /opt/hue-emulator/coap-client-linux
       ;;
    *)
        echo -e "\033[0;31m-------------------------------------------------------------------------------"
        echo -e "ERROR: Unsupported architecture $arch!"
        echo -e "You will need to manually compile the entertainment-srv binary, "
        echo -e "and install your own coap-client\033[0m"
        echo -e "Please visit https://diyhue.readthedocs.io/en/latest/AddFuncts/entertainment.html"
        echo -e "Once installed, open this script and manually run the last 10 lines."
        exit 1
esac

chmod +x /opt/hue-emulator/entertainment-srv
chmod +x /opt/hue-emulator/coap-client-linux
chmod +x /opt/hue-emulator/check_updates.sh
cp hue-emulator.service /lib/systemd/system/
cd ../../
rm -rf diyHue.zip diyHue-master
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service
systemctl start hue-emulator.service

echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
