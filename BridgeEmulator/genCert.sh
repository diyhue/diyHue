#!/bin/bash
mac=$1
dec_serial=`python3 -c "print(int(\"$mac\".strip('\u200e'), 16))"`
openssl req -new -days 3650 -config openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$mac" -keyout private.key -out public.crt -set_serial $dec_serial

touch /opt/hue-emulator/config/cert.pem

cat private.key > /opt/hue-emulator/config/cert.pem
cat public.crt >> /opt/hue-emulator/config/cert.pem

rm private.key public.crt
