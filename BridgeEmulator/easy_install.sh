#!/bin/bash
apt install -y git nmap python3 python3-requests python3-ws4py
cd /tmp
git clone https://github.com/mariusmotea/diyHue.git
cd diyHue/BridgeEmulator/
mkdir /opt/hue-emulator
cp -r web-ui functions cert.pem HueEmulator3.py coap-client-linux config.json /opt/hue-emulator/
cp hue-emulator.service /lib/systemd/system/
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service 
systemctl start hue-emulator.service
echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
