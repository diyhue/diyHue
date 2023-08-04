FROM debian:stable-slim as prod
WORKDIR /opt/hue-emulator

COPY requirements.txt /tmp/pip-tmp/

## Install requirements
RUN apt update \
    && apt install --no-install-recommends -y \
        python3-minimal python3-pip python3-setuptools \
        openssl nmap psmisc iproute2 libcoap3-bin \
    && pip3 --disable-pip-version-check install --no-cache-dir -r /tmp/pip-tmp/requirements.txt \
    && apt purge -y python3-pip python3-setuptools \
    && apt autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/pip-tmp

## Expose ports
EXPOSE 80 443 1900/udp 1982/udp 2100/udp
