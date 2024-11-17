# This image just moves the correct bins to a specific folder.
# Can also be used to compile the binaries (for an even better experience)
FROM busybox as binselector
WORKDIR /opt/hue-emulator

# Architecture automatically set by docker eg. linux/amd64, linux/arm/v7, linux/arm64
ARG TARGETPLATFORM

# ============================ Actual image from here ====================
FROM debian:stable-slim as prod
WORKDIR /opt/hue-emulator
ARG TARGETPLATFORM

COPY requirements.txt ./

## Install requirements
RUN apt update \
    && apt install --no-install-recommends -y \
        curl unzip python3-minimal python3-pip python3-dev python3-setuptools gcc \
        openssl nmap psmisc iproute2 bluez bluetooth libcoap3-bin faketime \
    && pip3 install -r requirements.txt --no-cache-dir --break-system-packages \
    && apt purge -y python3-pip python3-setuptools python3-dev gcc \
    && apt autoremove -y \
    && rm -rf /var/lib/apt/lists/*

## Install diyHue
COPY ./BridgeEmulator/flaskUI/ /opt/hue-emulator/flaskUI/
COPY ./BridgeEmulator/functions/ /opt/hue-emulator/functions/
COPY ./BridgeEmulator/lights/ /opt/hue-emulator/lights/
COPY ./BridgeEmulator/sensors/ /opt/hue-emulator/sensors/
COPY ./BridgeEmulator/HueObjects/ /opt/hue-emulator/HueObjects/
COPY ./BridgeEmulator/services/ /opt/hue-emulator/services/
COPY ./BridgeEmulator/configManager/ /opt/hue-emulator/configManager/
COPY ./BridgeEmulator/logManager/ /opt/hue-emulator/logManager/
COPY ./BridgeEmulator/HueEmulator3.py /opt/hue-emulator/
COPY ./BridgeEmulator/githubInstall.sh /opt/hue-emulator/

## Install the web interface
RUN curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip \
    && mkdir diyhueUI \
    && unzip -qo diyHueUI.zip -d diyhueUI \
    && rm diyHueUI.zip \
    && mv diyhueUI/dist/index.html flaskUI/templates/ \
    && cp -r diyhueUI/dist/assets flaskUI/ \
    && rm -r diyhueUI

## Copy correct (compiled) C file from previous image
COPY ./BridgeEmulator/genCert.sh ./BridgeEmulator/openssl.conf /opt/hue-emulator/

## Change Docker script permissions
RUN chmod +x /opt/hue-emulator/genCert.sh

## Expose ports
EXPOSE 80 443 1900/udp 1982/udp 2100/udp

CMD [ "python3", "-u", "/opt/hue-emulator/HueEmulator3.py", "--docker" ]
