FROM python:3.6-slim
WORKDIR /opt/hue-emulator

# Set Build Architecture, can be passed in build command with "--build-arg BUILDARCH=aarch64"
#   valid values are aarch64, arm, i686, x86_64

ARG BUILD_ARCH=aarch64

COPY requirements.txt BridgeEmulator .build/genCert.sh .build/openssl.conf ./

#Install requirments
RUN apt-get update && \
    apt-get install --no-install-recommends -y unzip curl nmap psmisc iproute2 libcoap-1-0-bin && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --no-cache-dir -r requirements.txt && \
    mv ./entertainment-${BUILD_ARCH} ./entertainment-srv && \
    ln -s $(which coap-client) /opt/hue-emulator/coap-client-linux && \
# Add Docker Build scripts
    chmod +x ./genCert.sh && \
# Remove unused binaries 
    find . -name 'entertainment-*' ! -name 'entertainment-srv' -delete && \
    find . -name 'coap-client-*' ! -name 'coap-client-linux' -delete

# Expose ports
EXPOSE 80 443 1900/udp 2100/udp

CMD [ "python3", "-u", "/opt/hue-emulator/HueEmulator3.py", "--docker" ]
