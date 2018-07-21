#!/bin/bash
mac=`cat /sys/class/net/eth0/address`
serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
apt install -y git nmap python3 python3-requests python3-ws4py
cd /tmp
git clone https://github.com/mariusmotea/diyHue.git
mkdir /opt/hue-emulator
cd diyHue/BridgeEmulator
dec_serial=`python -c "print(int(\"$serial\", 16))"`
openssl req -new  -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial
cp -r web-ui functions cert.pem HueEmulator3.py coap-client-linux config.json /opt/hue-emulator/
cp entertainment-`uname -m` /opt/hue-emulator/entertainment-srv
cp hue-emulator.service /lib/systemd/system/
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service 
systemctl start hue-emulator.service
echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
