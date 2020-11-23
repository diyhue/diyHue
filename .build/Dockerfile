# This image just moves the correct bins to a specific folder.
# Can also be used to compile the binaries (for an even better experience)
FROM busybox as binselector
WORKDIR /workdir

# Architecture automatically set by docker eg. linux/amd64, linux/arm/v7, linux/arm64
ARG TARGETPLATFORM

COPY binaries .build/select.sh ./

RUN chmod +x ./select.sh && \
    mkdir out && \
    ./select.sh

# ============================ Actual image from here ====================
FROM python:3.9-slim-buster
WORKDIR /diyhue
ARG TARGETPLATFORM

COPY requirements.txt .

## Install requirements  
RUN apt update && apt install --no-install-recommends -y \
        openssl \
        nmap \
        psmisc \
        iproute2 \
    && pip3 install --no-cache-dir -r requirements.txt \
    && apt autoremove -y \
    && rm -rf /var/lib/apt/lists/*

## Install diyHue
COPY ./src/core/ .

## Copy correct (compiled) C file from previous image
COPY --from=binselector /workdir/out /diyhue/

## Document ports
EXPOSE 80 443 1900/udp 1982/udp 2100/udp

## Document volume
VOLUME ["/config"]

## Debug
## RUN ls -la /opt/hue-emulator

CMD [ "python3", "-u", "/diyhue/main.py" ]
