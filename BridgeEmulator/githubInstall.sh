SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

curl -s $1/save
cd /
if [ $2 = allreadytoinstall ]; then
    echo "diyhue + ui update"
    curl -sL -o diyhue.zip https://github.com/diyhue/diyhue/archive/master.zip
    #curl -sL -o diyhue.zip https://github.com/hendriksen-mark/diyhue/archive/master.zip
    unzip -qo diyhue.zip
    rm diyhue.zip
    cp -r diyHue-master/BridgeEmulator/flaskUI "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/functions "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/lights "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/sensors "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/HueObjects "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/services "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/configManager "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/logManager "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/HueEmulator3.py "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/githubInstall.sh "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/genCert.sh "$SCRIPT_DIR"/
    cp -r diyHue-master/BridgeEmulator/openssl.conf "$SCRIPT_DIR"/
    chmod +x "$SCRIPT_DIR"/genCert.sh
    rm -r diyHue-master
else
    echo "ui update"
fi

mkdir diyhueUI
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
#curl -sL https://github.com/hendriksen-mark/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip -d diyhueUI
rm diyHueUI.zip
cp -r diyhueUI/dist/index.html "$SCRIPT_DIR"/flaskUI/templates/
cp -r diyhueUI/dist/assets "$SCRIPT_DIR"/flaskUI/
rm -r diyhueUI

curl -s $1/restart
