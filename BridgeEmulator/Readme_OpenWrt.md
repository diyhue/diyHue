opkg update
opkg install wget ca-bundle
cd /tmp
wget --no-check-certificate https://raw.githubusercontent.com/juanesf/diyHue/master/BridgeEmulator/easy_openwrt.sh
sh easy_openwrt.sh
