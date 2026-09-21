# Bridge Pro local onboarding test

This is an experimental, opt-in BSB003 profile. It is not a claim of Philips
Hue app compatibility.

## Preconditions

Use a separate diyHue container and an empty configuration volume. Do not
reuse a Classic bridge volume, bridge identity, certificate, or Zigbee network.
Start the candidate with `BRIDGE_PROFILE=pro`, HTTPS enabled, and a reachable
LAN address. The profile advertises `_hue._tcp.local.` on HTTPS port 443 and
does not advertise Classic SSDP.

## Pairing window

The emulator has no physical button. An administrator with local container
control can emulate exactly one physical press by sending `SIGUSR1` to the
running bridge process:

```
docker kill --signal=USR1 <isolated-pro-container>
```

This opens the normal local `/api` registration window for 30 seconds. It is
not an HTTP endpoint and does not disable link-button checks. A successful
application registration is persisted normally; the button press itself is
not persisted.

## Manual acceptance record

1. Put the phone and isolated bridge on the same LAN/VLAN with multicast DNS.
2. Start the official Hue app and choose to add a bridge. If it asks for a
   QR code, follow its documented **No QR code** path and select **Bridge Pro**;
   diyHue does not manufacture a hardware ownership QR code.
3. Record whether the BSB003 bridge is shown. If not, capture only sanitized
   mDNS service type, port, model id, and bridge-id suffix.
4. When the app requests the bridge-button press, send `SIGUSR1` as above and
   complete the app flow within 30 seconds.
5. Record the first failed app screen or successful completion, without
   application keys, certificates, addresses, or account identifiers.
6. If pairing succeeds, verify V2 resource loading, a non-production test
   light, then both app and bridge restart.

The no-QR app path is documented by Philips Hue, but QR-code enrolment, the
Hue app's certificate trust policy, account/cloud requirements, and real app
pairing are not validated by this repository test. Do not install forged or
Philips-issued certificates, and do not report native app compatibility without
completing the manual record.
