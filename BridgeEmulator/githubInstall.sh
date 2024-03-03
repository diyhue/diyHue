curl -s localhost/save
cd /
if [ ! -d diyhue ]; then
 mkdir diyhue
fi
#curl -s -J -L -o diyhue.tar.gz "https://github.com/diyhue/diyHue/archive/refs/heads/master.tar.gz"
curl -s -J -L -o diyhue.tar.gz "https://github.com/hendriksen-mark/diyhue/archive/refs/heads/master.tar.gz"
tar xzf diyhue.tar.gz --strip-components=1 -C diyhue
#cd diyhue
cp -r diyhue/BridgeEmulator/flaskUI/ /opt/hue-emulator/flaskUI/
cp -r diyhue/BridgeEmulator/functions/ /opt/hue-emulator/functions/
cp -r diyhue/BridgeEmulator/lights/ /opt/hue-emulator/lights/
cp -r diyhue/BridgeEmulator/sensors/ /opt/hue-emulator/sensors/
cp -r diyhue/BridgeEmulator/HueObjects/ /opt/hue-emulator/HueObjects/
cp -r diyhue/BridgeEmulator/services/ /opt/hue-emulatorservices/
cp -r diyhue/BridgeEmulator/configManager/ /opt/hue-emulator/configManager/
cp -r diyhue/BridgeEmulator/logManager/ /opt/hue-emulator/logManager/
mv diyhue/BridgeEmulator/HueEmulator3.py /opt/hue-emulator/
mv diyhue/BridgeEmulator/githubInstall.sh /opt/hue-emulator/
mv diyhue/BridgeEmulator/githubUIInstall.sh /opt/hue-emulator/
mv diyhue/BridgeEmulator/genCert.sh /opt/hue-emulator/
mv diyhue/BridgeEmulator/openssl.conf /opt/hue-emulator/
chmod +x /opt/hue-emulator/genCert.sh

#cd /
if [ ! -d diyhueUI ]; then
 mkdir diyhueUI
fi
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip -d diyhueUI
#cd diyhueUI
mv diyhueUI/index.html /opt/hue-emulator/flaskUI/templates/
cp -r diyhueUI/static/ /opt/hue-emulator/flaskUI/static/

curl -s localhost/reboot
