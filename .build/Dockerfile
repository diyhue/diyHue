# This image just moves the correct bins to a specific folder.
# Can also be used to compile the binaries (for an even better experience)
FROM busybox as binselector
WORKDIR /opt/hue-emulator

# Architecture automatically set by docker eg. linux/amd64, linux/arm/v7, linux/arm64
ARG TARGETPLATFORM

COPY Installers .build/select.sh ./

RUN chmod +x ./select.sh && \
    mkdir out && \
    ./select.sh

# ============================ Actual image from here ====================
FROM debian:stable-slim
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
COPY ./src/core/ /diyhue/

## Copy correct (compiled) C file from previous image
COPY ./src/core/genCert.sh ./src/core/openssl.conf /diyhue/
RUN echo workaround for https://github.com/moby/moby/issues/37965
COPY --from=binselector /opt/hue-emulator/out /diyhue/

## Change Docker script permissions
RUN chmod +x /diyhue/genCert.sh

## Document ports
EXPOSE 80 443 1900/udp 1982/udp 2100/udp

## Document volume
VOLUME ["/config"]

## Debug
## RUN ls -la /opt/hue-emulator

CMD [ "python3", "-u", "/diyhue/main.py" ]
