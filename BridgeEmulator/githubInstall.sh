curl -s localhost/save
cd /
[ ! -d diyhue ] && mkdir diyhue
curl -s -J -L -o $diyhue.tar.gz "https://github.com/diyhue/diyHue/archive/refs/heads/master.tar.gz"
tar xzf $diyhue.tar.gz --strip-components=1 -C diyhue
cd diyhue
[ -d /opt/hue-emulator/flaskUI ] && rm -r /opt/hue-emulator/functions
mv ./BridgeEmulator/flaskUI/ /opt/hue-emulator/flaskUI/

[ -d /opt/hue-emulator/functions ] && rm -r /opt/hue-emulator/functions
mv ./BridgeEmulator/functions/ /opt/hue-emulator/

[ -d /opt/hue-emulator/lights ] && rm -r /opt/hue-emulator/lights
mv ./BridgeEmulator/lights/ /opt/hue-emulator/

[ -d /opt/hue-emulator/sensors ] && rm -r /opt/hue-emulator/sensors
mv ./BridgeEmulator/sensors/ /opt/hue-emulator/

[ -d /opt/hue-emulator/HueObjects ] && rm -r /opt/hue-emulator/HueObjects
mv ./BridgeEmulator/HueObjects/ /opt/hue-emulator/

[ -d /opt/hue-emulator/services ] && rm -r /opt/hue-emulator/services
mv ./BridgeEmulator/services/ /opt/hue-emulator

[ -d /opt/hue-emulator/configManager ] && rm -r /opt/hue-emulator/configManager
mv ./BridgeEmulator/configManager/ /opt/hue-emulator/

[ -d /opt/hue-emulator/logManager ] && rm -r /opt/hue-emulator/logManager
mv ./BridgeEmulator/logManager/ /opt/hue-emulator/

mv ./BridgeEmulator/HueEmulator3.py /opt/hue-emulator/
mv ./BridgeEmulator/githubInstall.sh /opt/hue-emulator/
mv ./BridgeEmulator/githubUIInstall.sh /opt/hue-emulator/
echo "cp diyhue"

cd /
[ ! -d /diyhueUI ] && mkdir diyhueUI
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip -d diyhueUI
cd diyhueUI
mv index.html /opt/hue-emulator/flaskUI/templates/
[ -d /opt/hue-emulator/flaskUI/static ] && rm -r /opt/hue-emulator/flaskUI/static
mv static /opt/hue-emulator/flaskUI/

curl -s "localhost.lan/reboot"
