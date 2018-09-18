FROM arm32v7/debian:stretch-slim
WORKDIR /tmp

ADD https://raw.githubusercontent.com/mariusmotea/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf .

#Install requirments
RUN apt update && apt install -y openssl unzip curl python3 python3-setuptools nmap psmisc iproute2 && rm -rf /var/lib/apt/lists/*

## Install Python requirements.txt
RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
RUN python3 get-pip.py --user
ENV PATH "$PATH:/root/.local/bin"
COPY requirements.txt .
RUN pip3 install -r requirements.txt

## Install diyHue
COPY ./BridgeEmulator/ /opt/hue-emulator/

#x86 specific
COPY ./BridgeEmulator/entertainment-arm /opt/hue-emulator/entertainment-srv
COPY ./BridgeEmulator/coap-client-arm /opt/hue-emulator/coap-client-linux

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
