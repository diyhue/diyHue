#!/bin/bash
arch=`uname -m`
export LC_ALL=C
export CC=gcc
echo -e "\033[32m Updating repository.\033[0m"
opkg update
wait
echo -e "\033[32m Installing dependencies.\033[0m"
opkg install gcc make automake ca-bundle git git-http nano nmap openssl-util curl unzip libustream-mbedtls
wait
echo -e "\033[32m Creating directories.\033[0m"
mkdir /opt
mkdir /opt/tmp
mkdir /opt/hue-emulator
wait
echo -e "\033[32m Download mbedtls to compile binary entertainment.\033[0m"
wait
cd /opt/hue-emulator
wget --no-check-certificate https://github.com/ARMmbed/mbedtls/archive/1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482.zip
wait
unzip 1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482
wait
mv mbedtls-1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482 mbedtls
rm -Rf 1ab9b5714852c6810c0a0bfd8c3b5c60a9a15482.zip
cd /opt/hue-emulator/mbedtls
echo -e "\033[32m Download entertainment source file to compile binary.\033[0m"
wget --no-check-certificate https://raw.githubusercontent.com/diyhue/diyHue/master/BridgeEmulator/ssl_server2_diyhue.c
wait
echo -e "\033[32m Compiling.\033[0m"
make no_test
wait
gcc -I../mbedtls/include ssl_server2_diyhue.c -o ssl_server2_diyhue -L../mbedtls/library -lmbedtls -lmbedx509 -lmbedcrypto
wait
cp /opt/hue-emulator/mbedtls/ssl_server2_diyhue /opt/hue-emulator/entertain-srv-$arch
wait
cd /opt/hue-emulator
rm -Rf /opt/hue-emulator/mbedtls
wait
echo -e "\033[32m Compiled binary for: $arch.\033[0m"
echo -e "\033[32m Uploading binary $arch to remote server.\033[0m"
curl --upload-file /opt/hue-emulator/entertain-srv-$arch https://transfer.sh/entertain-srv-$arch
rm -Rf /opt/hue-emulator/
rm -Rf /opt/tmp
rm -Rf /opt/
wait
exit 0
