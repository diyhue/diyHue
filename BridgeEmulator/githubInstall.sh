curl -s $1/save
cd /
if [ $2 = allreadytoinstall ]; then
    echo "diyhue + ui update"
    curl -sL -o diyhue.zip https://github.com/diyhue/diyhue/archive/master.zip
    #curl -sL -o diyhue.zip https://github.com/hendriksen-mark/diyhue/archive/master.zip
    unzip -qo diyhue.zip
    rm diyhue.zip
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
