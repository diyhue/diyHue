#!/usr/bin/env bash
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

mac=$1
config="${2:-$SCRIPT_DIR/config}"
dec_serial=`python3 -c "print(int(\"$mac\".strip('\u200e'), 16))"`
faketime '2017-01-01 00:00:00' openssl req -new -days 7670 -config $SCRIPT_DIR/openssl.conf  -nodes -x509 -newkey  ec -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve   -subj "/C=NL/O=Philips Hue/CN=$mac" -keyout private.key -out public.crt -set_serial $dec_serial

mkdir -p $config
touch $config/cert.pem

cat private.key > "$config/cert.pem"
cat public.crt >> "$config/cert.pem"

rm private.key public.crt
