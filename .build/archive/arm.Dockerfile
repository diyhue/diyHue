FROM balenalib/raspberrypi3-debian-python:3-latest
WORKDIR /opt/hue-emulator

RUN [ "cross-build-start" ]

## Install requirments
RUN apt update && apt install -y openssl nmap psmisc iproute2 tzdata \
    && pip install pytz astral==1.6.1 ws4py==0.5.1 requests==2.20.0 paho-mqtt==1.5.0 --no-cache-dir \
    && rm -rf /var/lib/apt/lists/*

## Install diyHue
COPY ./BridgeEmulator/web-ui/ /opt/hue-emulator/web-ui/
COPY ./BridgeEmulator/functions/ /opt/hue-emulator/functions/
COPY ./BridgeEmulator/protocols/ /opt/hue-emulator/protocols/
COPY ./BridgeEmulator/HueEmulator3.py ./BridgeEmulator/debug/clip.html /opt/hue-emulator/

## armhf specific
COPY ./BridgeEmulator/entertainment-arm /opt/hue-emulator/entertain-srv
COPY ./BridgeEmulator/coap-client-arm /opt/hue-emulator/coap-client-linux

## Add Docker Build scripts
COPY ./.build/genCert.sh ./.build/openssl.conf /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/genCert.sh

## Debug
# RUN ls -la /opt/hue-emulator

RUN [ "cross-build-end" ]

EXPOSE 80 443 1900/udp 1982/udp 2100/udp

CMD [ "python3", "-u", "/opt/hue-emulator/HueEmulator3.py", "--docker" ]
