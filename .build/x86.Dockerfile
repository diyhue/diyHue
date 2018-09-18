FROM python:3.6.6-alpine3.8
WORKDIR /tmp

ADD https://raw.githubusercontent.com/mariusmotea/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf .

#Install requirments
RUN apk update && apk add openssl unzip curl nmap psmisc iproute2 && rm -rf /var/lib/apt/lists/*

## Install Python requirements.txt
COPY requirements.txt .
RUN pip3 install -r requirements.txt

## Install diyHue
COPY ./BridgeEmulator/HueEmulator3.py /opt/hue-emulator/
COPY ./BridgeEmulator/functions/* /opt/hue-emulator/functions/
COPY ./BridgeEmulator/protocols/* /opt/hue-emulator/protocols/
COPY ./BridgeEmulator/web-ui/* /opt/hue-emulator/web-ui/

#x86_64 specific
COPY ./BridgeEmulator/entertainment-x86_64 /opt/hue-emulator/entertainment-srv
COPY ./BridgeEmulator/coap-client-x86_64 /opt/hue-emulator/coap-client-linux

# Add Docker Build scripts
ADD https://raw.githubusercontent.com/mariusmotea/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf /opt/hue-emulator
COPY ./.build/startup.sh /opt/hue-emulator/
COPY ./.build/genCert.sh /opt/hue-emulator/
RUN chmod +x /opt/hue-emulator/startup.sh && chmod +x /opt/hue-emulator/genCert.sh
RUN sed -i "s|docker = False|docker = True |g" /opt/hue-emulator/HueEmulator3.py

## cleanup
RUN rm -rf /tmp/*
RUN ls -la /opt/hue-emulator
ENTRYPOINT /opt/hue-emulator/startup.sh $MAC $IP
