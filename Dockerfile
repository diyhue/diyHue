FROM arm32v7/debian:stretch-slim
WORKDIR /opt/hue-emulator

#Get required scripts
COPY startup.sh .
COPY genCert.sh .
ADD https://raw.githubusercontent.com/mariusmotea/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf .

#Install requirments
RUN apt update && apt install -y openssl unzip curl python3 python3-setuptools nmap psmisc iproute2 && rm -rf /var/lib/apt/lists/*

## install astral
RUN cd /tmp && pwd && curl https://codeload.github.com/sffjunkie/astral/zip/1.6.1 -o astral.zip && unzip -q -o astral.zip && cd astral-1.6.1/ && python3 setup.py install

## install python3-ws4py
RUN cd /tmp && curl https://codeload.github.com/Lawouach/WebSocket-for-Python/zip/0.5.1 -o ws4py.zip && unzip -q -o ws4py.zip && cd WebSocket-for-Python-0.5.1/ && python3 setup.py install

## install python3-requests
RUN cd /tmp && curl https://codeload.github.com/requests/requests/zip/v2.19.1 -o requests.zip && unzip -q -o requests.zip && cd requests-2.19.1/ && python3 setup.py install

## Install diyHue
RUN cd /tmp && curl https://codeload.github.com/mariusmotea/diyHue/zip/master -o master.zip && unzip -q -o master.zip && cd diyHue-master/BridgeEmulator/ && cp -r web-ui functions protocols HueEmulator3.py config.json /opt/hue-emulator/ && cp entertainment-arm /opt/hue-emulator/entertainment-srv && cp coap-client-arm /opt/hue-emulator/coap-client-linux
RUN chmod +x /opt/hue-emulator/startup.sh && chmod +x /opt/hue-emulator/genCert.sh
RUN sed -i "s|docker = False|docker = True |g" HueEmulator3.py

## cleanup
RUN rm -rf /tmp/*

ENTRYPOINT /opt/hue-emulator/startup.sh $MAC $IP
