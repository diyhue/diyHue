FROM debian:stable-slim as prod
WORKDIR /opt/hue-emulator
ARG TARGETPLATFORM

COPY requirements.txt ./

## Install requirements  
RUN apt update && apt install --no-install-recommends -y \
    python3-minimal python3-pip python3-setuptools \
    openssl nmap psmisc iproute2 \
    && pip3 install -r requirements.txt --no-cache-dir \
    && apt purge -y python3-pip python3-setuptools \
    && apt autoremove -y \
    && rm -rf /var/lib/apt/lists/*

## Install diyHue
COPY ./BridgeEmulator/web-ui/ /opt/hue-emulator/web-ui/
COPY ./BridgeEmulator/functions/ /opt/hue-emulator/functions/
COPY ./BridgeEmulator/protocols/ /opt/hue-emulator/protocols/
COPY ./BridgeEmulator/HueEmulator3.py ./BridgeEmulator/debug/clip.html /opt/hue-emulator/

## x86_64 specific
COPY ./BridgeEmulator/entertainment-x86_64 /opt/hue-emulator/entertain-srv
COPY ./BridgeEmulator/coap-client-x86_64 /opt/hue-emulator/coap-client-linux

## Add Docker Build scripts
COPY ./.build/genCert.sh ./.build/openssl.conf /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/genCert.sh

## Expose ports
EXPOSE 80 443 1900/udp 1982/udp 2100/udp

## Debug
## RUN ls -la /opt/hue-emulator

CMD [ "python3", "-u", "/opt/hue-emulator/HueEmulator3.py", "--docker" ]
