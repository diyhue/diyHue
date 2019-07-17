FROM balenalib/raspberrypi3-debian-python
WORKDIR /opt/hue-emulator

RUN [ "cross-build-start" ]

## Install requirments
RUN apt update && apt install -y python3 python3-setuptools openssl unzip curl nmap psmisc iproute2 tzdata && rm -rf /var/lib/apt/lists/*

## Install pytz
RUN pip install pytz --no-cache-dir

## Install astral
RUN cd /tmp && pwd && curl https://codeload.github.com/sffjunkie/astral/zip/1.6.1 -o astral.zip && unzip -q -o astral.zip && cd astral-1.6.1/ && python3 setup.py install && rm -rf /tmp/*

## Install python3-ws4py
RUN cd /tmp && curl https://codeload.github.com/Lawouach/WebSocket-for-Python/zip/0.5.1 -o ws4py.zip && unzip -q -o ws4py.zip && cd WebSocket-for-Python-0.5.1/ && python3 setup.py install && rm -rf /tmp/*

## Install python3-requests
RUN cd /tmp && curl https://codeload.github.com/requests/requests/zip/v2.19.1 -o requests.zip && unzip -q -o requests.zip && cd requests-2.19.1/ && python3 setup.py install && rm -rf /tmp/*

## Install diyHue
COPY ./BridgeEmulator/web-ui/ /opt/hue-emulator/web-ui/
COPY ./BridgeEmulator/functions/ /opt/hue-emulator/functions/
COPY ./BridgeEmulator/protocols/ /opt/hue-emulator/protocols/
COPY ./BridgeEmulator/HueEmulator3.py ./BridgeEmulator/debug/clip.html /opt/hue-emulator/

## armhf specific
COPY ./BridgeEmulator/entertainment-arm /opt/hue-emulator/entertainment-srv
COPY ./BridgeEmulator/coap-client-arm /opt/hue-emulator/coap-client-linux

## Add Docker Build scripts
COPY ./.build/genCert.sh ./.build/openssl.conf /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/genCert.sh

## Cleanup
RUN ls -la /opt/hue-emulator

RUN [ "cross-build-end" ]
CMD [ "python3", "-u", "/opt/hue-emulator/HueEmulator3.py", "--docker" ]
