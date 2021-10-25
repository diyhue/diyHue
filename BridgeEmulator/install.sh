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
  curl https://raw.githubusercontent.com/diyhue/diyHue/9ceed19b4211aa85a90fac9ea6d45cfeb746c9dd/BridgeEmulator/openssl.conf -o openssl.conf
  serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
  dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
  openssl req -new -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial -days 3650
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
  if [ $branchSelection == "beta" ]; then
    if [ ! -d "/opt/hue-emulator/config/" ]; then
      mkdir /opt/hue-emulator/config/ -p
    fi
    cp /opt/hue-emulator/cert.pem /opt/hue-emulator/config/
  fi

}

arch=`uname -m`

cd /tmp

### Choose Branch for Install
echo -e "\033[36mPlease choose a Branch to install\033[0m"
echo -e "\033[33mSelect Branch by entering the corresponding Number: [Default: Master]\033[0m  "
echo -e "[1] Master Branch - most stable Release "
echo -e "[2] Developer Branch - test latest features and fixes - Work in Progress!"
echo -e "[3] Beta Branch - Work with Hue App 4.0 - Work in Progress!"
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
	3)
        branchSelection="beta"
        echo -e "Beta selected"
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
  apt-get install -y unzip python3 python3-pip
elif type pacman &> /dev/null; then
  # Arch linux
  pacman -Syq --noconfirm || exit 1
  pacman -Sq --noconfirm unzip python3 python-pip gnu-netcat || exit 1
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

pip install -t requirements.txt


if [ -d "/opt/hue-emulator" ]; then
  if [ $branchSelection != "beta" ]; then
    if [ -f "/opt/hue-emulator/cert.pem" ]; then
      cp /opt/hue-emulator/cert.pem /tmp/cert.pem
    else
      generate_certificate
    fi
  fi

  systemctl stop hue-emulator.service
  echo -e "\033[33m Existing installation found, performing upgrade.\033[0m"
  if [ $branchSelection != "beta" ]; then
    cp /opt/hue-emulator/config.json /tmp
    rm -rf /opt/hue-emulator
    mkdir /opt/hue-emulator
    mv /tmp/config.json /opt/hue-emulator
    mv /tmp/cert.pem /opt/hue-emulator
  else
    cp -r /opt/hue-emulator/config /tmp/diyhue_backup
    rm -rf /opt/hue-emulator/*
    cp -r /tmp/diyhue_backup /opt/hue-emulator
  fi

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

  if [ $branchSelection != "beta" ]; then
    cp default-config.json /opt/hue-emulator/
  fi
  generate_certificate
fi

if [ $branchSelection == "beta" ]; then
  cp -r HueEmulator3.py HueObjects configManager flaskUI functions lights logManager sensors services /opt/hue-emulator/
else
  cp -r web-ui functions protocols HueEmulator3.py check_updates.sh debug /opt/hue-emulator/
fi

# Install correct binaries
case $arch in
    x86_64|i686|aarch64)
        cp entertainment-$arch /opt/hue-emulator/entertain-srv
        cp coap-client-$arch /opt/hue-emulator/coap-client-linux
       ;;
    arm64)
        cp entertainment-aarch64 /opt/hue-emulator/entertain-srv
        cp coap-client-aarch64 /opt/hue-emulator/coap-client-linux
       ;;
    armv*)
        cp entertainment-arm /opt/hue-emulator/entertain-srv
        cp coap-client-arm /opt/hue-emulator/coap-client-linux
       ;;
    *)
        echo -e "\033[0;31m-------------------------------------------------------------------------------"
        echo -e "ERROR: Unsupported architecture $arch!"
        echo -e "You will need to manually compile the entertain-srv binary, "
        echo -e "and install your own coap-client\033[0m"
        echo -e "Please visit https://diyhue.readthedocs.io/en/latest/AddFuncts/entertainment.html"
        echo -e "Once installed, open this script and manually run the last 10 lines."
        exit 1
esac

chmod +x /opt/hue-emulator/entertain-srv
chmod +x /opt/hue-emulator/coap-client-linux
cp hue-emulator.service /lib/systemd/system/
cd ../../
rm -rf diyHue.zip diyHue-$branchSelection
chmod 644 /lib/systemd/system/hue-emulator.service
systemctl daemon-reload
systemctl enable hue-emulator.service
systemctl start hue-emulator.service

echo -e "\033[32m Installation completed. Open Hue app and search for bridges.\033[0m"

