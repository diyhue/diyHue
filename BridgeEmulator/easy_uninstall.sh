#!/bin/bash
cd /tmp

### Uninstalling astral library for sunrise/sunset routines
echo -e "\033[36m Uninstalling Python Astral.\033[0m"
wget -q https://github.com/sffjunkie/astral/archive/master.zip -O astral.zip
unzip -q -o astral.zip
cd astral-master/
python3 setup.py install --record files.txt
# inspect files.txt to make sure it looks ok. Then:
tr '\n' '\0' < files.txt | xargs -0 sudo rm -f --
cd ../
rm -rf astral.zip astral-master/

### Uninstalling hue emulator
echo -e "\033[36m Uninstalling Hue Emulator.\033[0m"

rm -rf /opt/hue-emulator/

systemctl disable hue-emulator.service
rm /lib/systemd/system/hue-emulator.service
systemctl daemon-reload

### Uninstalling dependencies
echo -e "\033[36m Uninstalling dependencies.\033[0m"
apt remove -y unzip nmap python3 python3-requests python3-ws4py python3-setuptools && apt autoremove -y

echo -e "\033[32m Uninstal complete!\033[0m"
