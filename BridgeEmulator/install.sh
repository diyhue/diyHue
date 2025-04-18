#!/usr/bin/env bash

generate_certificate () {
  ### Build interfaces array
  interfaces=($(ls -A /sys/class/net))

  ### Remove loopback interface
  temp_array=()
  for value in "${interfaces[@]}"
  do
    [[ $value != lo ]] && [[ $value != docker0 ]] && temp_array+=($value)
  done
  interfaces=("${temp_array[@]}")
  unset temp_array

  echo "$interfaces"

  ### check if number of interfaces is more than 1
  if [ "${#interfaces[@]}" -gt "1" ]; then
    echo -e "\033[33mWARNING!\033[0m  "${#interfaces[@]}" network interfaces detected. A certificate will be generated based on the interface MAC address you select."
    echo -e "If you don't know what to choose then you can try the default interface\033[36m $(ip route get 8.8.8.8 | sed -n 's/.* dev \([^ ]*\).*/\1/p')\033[0m."

    PS3='Please choose the interface that will communicate with the Hue apps: '

    select answer in "${interfaces[@]}"; do
      for item in "${interfaces[@]}"; do
        if [[ $item == $answer ]]; then
          break 2
        fi
      done
    done
    echo "$answer"

    mac=`cat /sys/class/net/$answer/address`
  else
    mac=`cat /sys/class/net/$interfaces/address`
  fi

  echo "Generating certificat for MAC $mac"
  echo -e "\033[33mIf this is a diyhue reinstallation process then you will need to reinstall official Hue apps from PC and phone in order to wipe old certificate.\033[0m"
  serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
  dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
  faketime '2017-01-01 00:00:00' openssl req -new -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial -days 7670
  if [ $? -ne 0 ] ; then
    echo -e "\033[31m ERROR!! Local certificate generation failed! Attempting remote server generation\033[0m"
    ### test is server for certificate generation is reachable
    if ! nc -z mariusmotea.go.ro 9002 2>/dev/null; then
      echo -e "\033[31m ERROR!! Certificate generation service is down. Please try again later.\033[0m"
      exit 1
    fi
    curl "http://mariusmotea.go.ro:9002/gencert?mac=$mac" > /opt/hue-emulator/cert.pem
  else
    touch /opt/hue-emulator/cert.pem
    cat private.key > /opt/hue-emulator/cert.pem
    cat public.crt >> /opt/hue-emulator/cert.pem
    rm private.key public.crt
  fi

  if [ ! -d "/opt/hue-emulator/config/" ]; then
    mkdir /opt/hue-emulator/config/ -p
  fi
  cp /opt/hue-emulator/cert.pem /opt/hue-emulator/config/


}

arch=`uname -m`

cd /tmp

### Choose Branch for Install
echo -e "\033[36mPlease choose a Branch to install\033[0m"
echo -e "\033[33mSelect Branch by entering the corresponding Number: [Default: Master]\033[0m  "
echo -e "[1] Master Branch - most stable Release "
echo -e "[2] Developer Branch - test latest features and fixes - Work in Progress!"
echo -e "\033[36mNote: Please report any Bugs or Errors with Logs to our GitHub, Discourse or Slack. Thank you!\033[0m"
echo -n "I go with Nr.: "

branchSelection=""
read userSelection
case $userSelection in
        1)
        branchSelection="master"
        echo -e "Master selected"
        ;;
        2)
        branchSelection="dev"
        echo -e "Dev selected"
        ;;
				*)
        branchSelection="master"
        echo -e "Master selected"
        ;;
esac

### installing dependencies
echo -e "\033[36m Installing dependencies.\033[0m"
if type apt &> /dev/null; then
  # Debian-based distro
  apt-get install -y unzip python3 python3-pip openssl bluez bluetooth libcoap3-bin faketime
elif type pacman &> /dev/null; then
  # Arch linux
  pacman -Syq --noconfirm || exit 1
  pacman -Sq --noconfirm unzip python3 python-pip gnu-netcat libcoap faketime || exit 1
else
  # Or assume that packages are already installed (possibly with user confirmation)?
  # Or check them?
  echo -e "\033[31mUnable to detect package manager, aborting\033[0m"
  exit 1
fi

echo "https://github.com/diyhue/diyHue/archive/$branchSelection.zip"
# installing hue emulator
echo -e "\033[36m Installing Hue Emulator.\033[0m"
curl -sL https://github.com/diyhue/diyHue/archive/$branchSelection.zip -o diyHue.zip
unzip -qo diyHue.zip
cd diyHue-$branchSelection/BridgeEmulator/

echo -e "\033[36m Installing Python Dependencies.\033[0m"
python3 -m pip install --upgrade pip
pip3 install -r ../requirements.txt --break-system-packages


if [ -d "/opt/hue-emulator" ]; then

  systemctl stop hue-emulator.service
  echo -e "\033[33m Existing installation found, performing upgrade.\033[0m"

  cp -r /opt/hue-emulator/config /tmp/diyhue_backup
  rm -rf /opt/hue-emulator/*
  cp -r /tmp/diyhue_backup /opt/hue-emulator/config

else
  if cat /proc/net/tcp | grep -c "00000000:0050" > /dev/null; then
      echo -e "\033[31m ERROR!! Port 80 already in use. Close the application that use this port and try again.\033[0m"
      exit 1
  fi
  if cat /proc/net/tcp | grep -c "00000000:01BB" > /dev/null; then
      echo -e "\033[31m ERROR!! Port 443 already in use. Close the application that use this port and try again.\033[0m"
      exit 1
  fi
  mkdir /opt/hue-emulator

  generate_certificate
fi


cp -r HueEmulator3.py githubInstall.sh HueObjects configManager flaskUI functions lights logManager sensors services /opt/hue-emulator/

# Copy web interface files

curl -sL https://github.com/diyhue/diyHueUI/releases/latest/download/DiyHueUI-release.zip -o diyHueUI.zip
unzip -qo diyHueUI.zip
mv dist/index.html /opt/hue-emulator/flaskUI/templates/
cp -r dist/assets /opt/hue-emulator/flaskUI/
rm -r dist

cp hue-emulator.service /lib/systemd/system/
cd ../../
rm -rf diyHue.zip diyHue-$branchSelection
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service
systemctl start hue-emulator.service

echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"
