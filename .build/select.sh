#!/bin/sh

# echo "Target platform is: $TARGETPLATFORM"

case "$TARGETPLATFORM" in
 "linux/amd64") SELECTED="x86_64" ;;
 "linux/arm/v6") SELECTED="arm" ;;
 "linux/arm/v7") SELECTED="arm" ;;
 "linux/arm64") SELECTED="aarch64" ;;
    *) SELECTED="unsupported" ;;
esac

# echo "Got file suffix: $SELECTED"
mv ./entertainment-$SELECTED ./out/entertain-srv
mv ./coap-client-$SELECTED ./out/coap-client-linux

# echo "Files in out folder"
# ls -la ./out/
