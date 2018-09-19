FROM resin/rpi-raspbian
WORKDIR /tmp

#Install requirments
RUN apt update && apt install -y python3 python3-setuptools python3-pip openssl unzip curl nmap psmisc iproute2 && rm -rf /var/lib/apt/lists/*

#Install Python3
RUN apk add --no-cache python3 && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    rm -r /root/.cache

## Install Python requirements.txt
COPY requirements.txt .
RUN pip3 install -r requirements.txt

## Install diyHue
COPY ./BridgeEmulator/web-ui/ /opt/hue-emulator/web-ui/
COPY ./BridgeEmulator/functions/ /opt/hue-emulator/functions/
COPY ./BridgeEmulator/protocols/ /opt/hue-emulator/protocols/
COPY ./BridgeEmulator/HueEmulator3.py /opt/hue-emulator/
COPY ./BridgeEmulator/config.json /opt/hue-emulator/

#armhf specific
COPY ./BridgeEmulator/entertainment-arm /opt/hue-emulator/entertainment-srv
COPY ./BridgeEmulator/coap-client-arm /opt/hue-emulator/coap-client-linux

# Add Docker Build scripts
COPY ./.build/startup.sh /opt/hue-emulator/
COPY ./.build/genCert.sh /opt/hue-emulator/
COPY ./.build/openssl.conf /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/startup.sh && chmod +x /opt/hue-emulator/genCert.sh
RUN sed -i "s|docker = False|docker = True |g" /opt/hue-emulator/HueEmulator3.py

## cleanup
RUN rm -rf /tmp/*
RUN ls -la /opt/hue-emulator
ENTRYPOINT /opt/hue-emulator/startup.sh $MAC $IP
