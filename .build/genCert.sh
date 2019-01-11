#!/bin/bash
mac=$1

serial="${mac:0:2}${mac:3:2}${mac:6:2}fffe${mac:9:2}${mac:12:2}${mac:15:2}"
dec_serial=`python3 -c "print(int(\"$serial\", 16))"`
openssl req -new -days 3650 -config /opt/hue-emulator/openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$serial" -keyout private.key -out public.crt -set_serial $dec_serial

touch /opt/hue-emulator/cert.pem

cat private.key > /opt/hue-emulator/cert.pem
cat public.crt >> /opt/hue-emulator/cert.pem
rm private.key public.crt 
