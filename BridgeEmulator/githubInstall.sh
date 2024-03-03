curl -s localhost/save
cd /
[ ! -d diyhue ] && mkdir diyhue
curl -s -J -L -o $diyhue.tar.gz "https://github.com/diyhue/diyHue/archive/refs/heads/master.tar.gz"
tar xzf $diyhue.tar.gz --strip-components=1 -C diyhue
#cd diyhue
[ -d /opt/hue-emulator/flaskUI ] && rm -r /opt/hue-emulator/flaskUI
mv diyhue/BridgeEmulator/flaskUI /opt/hue-emulator/

[ -d /opt/hue-emulator/functions ] && rm -r /opt/hue-emulator/functions
mv diyhue/BridgeEmulator/functions /opt/hue-emulator/

[ -d /opt/hue-emulator/lights ] && rm -r /opt/hue-emulator/lights
mv diyhue/BridgeEmulator/lights /opt/hue-emulator/

[ -d /opt/hue-emulator/sensors ] && rm -r /opt/hue-emulator/sensors
mv diyhue/BridgeEmulator/sensors /opt/hue-emulator/

[ -d /opt/hue-emulator/HueObjects ] && rm -r /opt/hue-emulator/HueObjects
mv diyhue/BridgeEmulator/HueObjects /opt/hue-emulator/

[ -d /opt/hue-emulator/services ] && rm -r /opt/hue-emulator/services
mv diyhue/BridgeEmulator/services /opt/hue-emulator

[ -d /opt/hue-emulator/configManager ] && rm -r /opt/hue-emulator/configManager
mv diyhue/BridgeEmulator/configManager /opt/hue-emulator/

[ -d /opt/hue-emulator/logManager ] && rm -r /opt/hue-emulator/logManager
mv diyhue/BridgeEmulator/logManager /opt/hue-emulator/

mv diyhue/BridgeEmulator/HueEmulator3.py /opt/hue-emulator/
mv diyhue/BridgeEmulator/githubInstall.sh /opt/hue-emulator/
mv diyhue/BridgeEmulator/githubUIInstall.sh /opt/hue-emulator/
mv diyhue/BridgeEmulator/genCert.sh /opt/hue-emulator/
mv diyhue/BridgeEmulator/openssl.conf /opt/hue-emulator/
chmod +x /opt/hue-emulator/genCert.sh

#cd /
[ ! -d /diyhueUI ] && mkdir diyhueUI
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip -d diyhueUI
#cd diyhueUI
mv diyhueUI/index.html /opt/hue-emulator/flaskUI/templates/
[ -d /opt/hue-emulator/flaskUI/static ] && rm -r /opt/hue-emulator/flaskUI/static
mv diyhueUI/static /opt/hue-emulator/flaskUI/

curl -s "localhost.lan/reboot"
