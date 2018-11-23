#!/bin/bash
mac=`cat /sys/class/net/$(ip route get 8.8.8.8 | sed -n 's/.* dev \([^ ]*\).*/\1/p')/address`
arch=`uname -m`

cd /tmp

### installing dependencies
echo -e "\033[36m Installing dependencies.\033[0m"
apt install -y unzip nmap python3 python3-requests python3-ws4py python3-setuptools

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
		echo -e "\033[31m WARNING!! Nginx is not necessary anymore, it will be stopped.\033[0m"
        	systemctl stop nginx
		systemctl disable nginx
		cp /opt/hue-emulator/private.key /tmp/cert.pem
                cat /opt/hue-emulator/public.crt >> /tmp/cert.pem
	elif [ -f "/opt/hue-emulator/cert.pem" ]; then
		cp /opt/hue-emulator/cert.pem /tmp/cert.pem
        else
		curl https://raw.githubusercontent.com/mariusmotea/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf -o openssl.conf
		serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
		dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
		openssl req -new  -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial
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
        cp config.json /opt/hue-emulator/
	
	curl https://raw.githubusercontent.com/mariusmotea/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf -o openssl.conf
	serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
	dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
	openssl req -new  -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial -days 3650
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
cp -r web-ui functions protocols HueEmulator3.py /opt/hue-emulator/
if [ $(uname -m) = "x86_64" ]; then
	cp entertainment-x86_64 /opt/hue-emulator/entertainment-srv
	cp coap-client-x86_64 /opt/hue-emulator/coap-client-linux
else
	if [ $(uname -m) = "i686" ]; then
		cp entertainment-x86 /opt/hue-emulator/entertainment-srv
        cp coap-client-linux-x86 /opt/hue-emulator/coap-client-linux
        else
        cp entertainment-arm /opt/hue-emulator/entertainment-srv
        cp coap-client-arm /opt/hue-emulator/coap-client-linux
	fi
fi
chmod +x /opt/hue-emulator/entertainment-srv
chmod +x /opt/hue-emulator/coap-client-linux
cp hue-emulator.service /lib/systemd/system/
cd ../../
rm -rf diyHue.zip diyHue-master
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service
systemctl start hue-emulator.service

echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
