#!/usr/bin/env bash

if [ -n ${1+x} ]; then 
    mac=$1
    echo -e "\033[33m--MAC given as $mac--\033[0m"
fi

echo -e "\033[33m--Setting up diyHue--\033[0m" 

if [ -f "/opt/hue-emulator/export/cert.pem" ]; then
    echo -e "\033[33m--Restoring certificate--\033[0m"
    cp /opt/hue-emulator/export/cert.pem /opt/hue-emulator/cert.pem
    echo -e "\033[33m--Certificate restored--\033[0m"
else
    echo -e "\033[33m--Generating certificate--\033[0m"
    /opt/hue-emulator/genCert.sh $mac
    cp /opt/hue-emulator/cert.pem /opt/hue-emulator/export/cert.pem
    echo -e "\033[33m--Certificate created--\033[0m"
fi

if [ -f "/opt/hue-emulator/export/config.json" ]; then
    echo -e "\033[33m--Restoring config--\033[0m" 
    cp /opt/hue-emulator/export/config.json /opt/hue-emulator/config.json
    echo -e "\033[33m--Config restored--\033[0m" 
else
    echo -e "\033[33m--Downloading default config--\033[0m"
    curl -o /opt/hue-emulator/config.json https://raw.githubusercontent.com/mariusmotea/diyHue/master/BridgeEmulator/config.json
    cp /opt/hue-emulator/config.json /opt/hue-emulator/export/config.json
    echo -e "\033[33m--Config downloaded--\033[0m" 
fi

cd /opt/hue-emulator

if [ $3=true ]; then
    echo -e "\033[33m--Debug set to $3, enabling debug--\033[0m"
    sed -i "s|debug = .* #|debug = True # |g" /opt/hue-emulator/HueEmulator3.py
else
    echo -e "\033[33m--Debug set to $3, disabling debug--\033[0m"
    sed -i "s|debug = .* #|debug = False # |g" /opt/hue-emulator/HueEmulator3.py
fi

echo -e "\033[32m--Startup complete. Open Hue app and search for bridges--\033[0m"
if [ -z $1 -a -z $2 ]; then
    echo -e "\033[32m--Starting without provided MAC & IP--\033[0m"
    exec python3 /opt/hue-emulator/HueEmulator3.py
else
    echo -e "\033[32m--Starting with provided MAC & IP--\033[0m"
    exec python3 /opt/hue-emulator/HueEmulator3.py $1 $2
fi
