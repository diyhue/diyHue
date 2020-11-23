FROM python:3.9-slim-buster AS dev_base
WORKDIR /diyhue

COPY requirements.txt requirements-dev.txt ./

## Install requirements
RUN apt update && apt install --no-install-recommends -y \
    openssl nmap psmisc iproute2 \
    && pip3 install --no-cache-dir -r requirements.txt -r requirements-dev.txt

FROM dev_base AS dev_pycharm

RUN pip3 install pydevd-pycharm~=201.7846.77

## Expose ports
EXPOSE 80 443 1900/udp 1982/udp 2100/udp
