FROM debian:stable-slim
WORKDIR /opt/hue-emulator

## Install requirements
RUN apt update && apt install -y python3 python3-setuptools python3-pip openssl unzip curl nmap psmisc iproute2 && rm -rf /var/lib/apt/lists/*

## Install python3-requests
RUN cd /tmp && curl https://codeload.github.com/requests/requests/zip/v2.19.1 -o requests.zip && unzip -q -o requests.zip && cd requests-2.19.1/ && python3 setup.py install && rm -rf /tmp/*

## Install astral & ws4py python libraries
RUN pip3 install astral==1.6.1 ws4py==0.5.1 --no-cache-dir

## Install diyHue
COPY ./BridgeEmulator/web-ui/ /opt/hue-emulator/web-ui/
COPY ./BridgeEmulator/functions/ /opt/hue-emulator/functions/
COPY ./BridgeEmulator/protocols/ /opt/hue-emulator/protocols/
COPY ./BridgeEmulator/HueEmulator3.py ./BridgeEmulator/debug/clip.html /opt/hue-emulator/

## x86_64 specific
COPY ./BridgeEmulator/entertainment-x86_64 /opt/hue-emulator/entertainment-srv
COPY ./BridgeEmulator/coap-client-x86_64 /opt/hue-emulator/coap-client-linux

## Add Docker Build scripts
COPY ./.build/genCert.sh ./.build/openssl.conf /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/genCert.sh

## Expose ports
EXPOSE 80
EXPOSE 443
EXPOSE 1900/udp
EXPOSE 2100/udp

## Cleanup
RUN ls -la /opt/hue-emulator
CMD [ "python3", "-u", "/opt/hue-emulator/HueEmulator3.py", "--docker" ]
