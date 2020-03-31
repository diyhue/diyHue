# This image just moves the correct bins to a specific folder.
# Can also be used to compile the binaries (for an even better experience)
FROM debian:stable-slim as binselector
WORKDIR /opt/hue-emulator

# Architecture automatically set by docker eg. linux/amd64, linux/arm/v7, linux/arm64
ARG TARGETPLATFORM

COPY BridgeEmulator .build/select.sh ./

RUN chmod +x ./select.sh && \
    mkdir out && \
    ./select.sh

# ============================ Actual image from here ====================
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

## Copy correct (compiled) C file from previous image
COPY --from=binselector /opt/hue-emulator/out /opt/hue-emulator/

## Add Docker Build scripts
COPY ./.build/genCert.sh ./.build/openssl.conf /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/genCert.sh

## Expose ports
EXPOSE 80 443 1900/udp 1982/udp 2100/udp

## Debug
## RUN ls -la /opt/hue-emulator

CMD [ "python3", "-u", "/opt/hue-emulator/HueEmulator3.py", "--docker" ]
