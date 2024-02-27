curl -s localhost/save
cd /
[ ! -d /diyhueUI ] && mkdir diyhueUI
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip -d diyhueUI
cd diyhueUI
mv index.html /opt/hue-emulator/flaskUI/templates/
[ -d /opt/hue-emulator/flaskUI/static ] && rm -r /opt/hue-emulator/flaskUI/static
mv static /opt/hue-emulator/flaskUI/

curl -s localhost/reboot
