#!/bin/bash

echo "Checking for Updates"
curl -s https://raw.githubusercontent.com/diyhue/diyHue/master/BridgeEmulator/easy_install.sh | sudo bash /dev/stdin
