FROM resin/rpi-raspbian
WORKDIR /tmp

#Install requirments
RUN apt update && apt install -y python3 python3-setuptools openssl unzip curl nmap psmisc iproute2 && rm -rf /var/lib/apt/lists/*

## install astral
RUN cd /tmp && pwd && curl https://codeload.github.com/sffjunkie/astral/zip/1.6.1 -o astral.zip && unzip -q -o astral.zip && cd astral-1.6.1/ && python3 setup.py install && rm -rf /tmp/*

## install python3-ws4py
RUN cd /tmp && curl https://codeload.github.com/Lawouach/WebSocket-for-Python/zip/0.5.1 -o ws4py.zip && unzip -q -o ws4py.zip && cd WebSocket-for-Python-0.5.1/ && python3 setup.py install && rm -rf /tmp/*

## install python3-requests
RUN cd /tmp && curl https://codeload.github.com/requests/requests/zip/v2.19.1 -o requests.zip && unzip -q -o requests.zip && cd requests-2.19.1/ && python3 setup.py install && rm -rf /tmp/*

## Install diyHue
COPY ./BridgeEmulator/web-ui/ /opt/hue-emulator/web-ui/
COPY ./BridgeEmulator/functions/ /opt/hue-emulator/functions/
COPY ./BridgeEmulator/protocols/ /opt/hue-emulator/protocols/
COPY ./BridgeEmulator/HueEmulator3.py ./BridgeEmulator/config.json /opt/hue-emulator/

#armhf specific
COPY ./BridgeEmulator/entertainment-arm /opt/hue-emulator/entertainment-srv
COPY ./BridgeEmulator/coap-client-arm /opt/hue-emulator/coap-client-linux

# Add Docker Build scripts
COPY ./.build/startup.sh ./.build/genCert.sh ./.build/openssl.conf /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/startup.sh && chmod +x /opt/hue-emulator/genCert.sh && sed -i "s|docker = False|docker = True |g" /opt/hue-emulator/HueEmulator3.py

## cleanup
RUN ls -la /opt/hue-emulator
ENTRYPOINT /opt/hue-emulator/startup.sh $MAC $IP
