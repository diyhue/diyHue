curl -s $1/save

### installing dependencies
if type apt &> /dev/null; then
  # Debian-based distro
  apt-get update
  apt-get install --no-install-recommends -y curl unzip python3-minimal python3-pip python3-dev python3-setuptools gcc openssl nmap psmisc iproute2 bluez bluetooth libcoap3-bin faketime
elif type pacman &> /dev/null; then
  # Arch linux
  pacman -Syq --noconfirm || exit 1
  pacman -Sq --noconfirm python3-pip python3-setuptools python3-dev gcc || exit 1
elif type opkg &> /dev/null; then
  # openwrt
  opkg update
  opkg install python3-pip python3-setuptools python3-dev gcc
else
  # Or assume that packages are already installed (possibly with user confirmation)?
  # Or check them?
  echo -e "\033[31mUnable to detect package manager, aborting\033[0m"
  exit 1
fi

cd /
if [ $2 = allreadytoinstall ]; then
    echo "diyhue + ui update"
    curl -sL -o diyhue.zip https://github.com/diyhue/diyhue/archive/master.zip
    #curl -sL -o diyhue.zip https://github.com/hendriksen-mark/diyhue/archive/master.zip
    unzip -qo diyhue.zip
    rm diyhue.zip

    python3 -m pip install --upgrade pip
    python3 -m pip install --upgrade pip --break-system-packages
    pip3 install -r diyHue-master/requirements.txt --no-cache-dir --break-system-packages

    cp -r diyHue-master/BridgeEmulator/flaskUI /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/functions /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/lights /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/sensors /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/HueObjects /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/services /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/configManager /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/logManager /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/HueEmulator3.py /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/githubInstall.sh /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/genCert.sh /opt/hue-emulator/
    cp -r diyHue-master/BridgeEmulator/openssl.conf /opt/hue-emulator/
    chmod +x /opt/hue-emulator/genCert.sh
    rm -r diyHue-master
else
    echo "ui update"
fi

mkdir diyhueUI
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
#curl -sL https://github.com/hendriksen-mark/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip -d diyhueUI
rm diyHueUI.zip
cp -r diyhueUI/dist/index.html /opt/hue-emulator/flaskUI/templates/
cp -r diyhueUI/dist/assets /opt/hue-emulator/flaskUI/
rm -r diyhueUI

curl -s $1/restart
