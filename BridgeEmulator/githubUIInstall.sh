curl -s localhost/save
#cd /
if [ ! -d diyhueUI ]; then
 mkdir diyhueUI
fi
curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip -d diyhueUI
#cd diyhueUI
mv diyhueUI/index.html /opt/hue-emulator/flaskUI/templates/
cp -r diyhueUI/static/ /opt/hue-emulator/flaskUI/static/

curl -s localhost/restart
