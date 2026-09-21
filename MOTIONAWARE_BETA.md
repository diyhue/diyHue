# MotionAware API/runtime beta

This is an opt-in Bridge Pro API/runtime beta, not a claim of support in the
official Philips Hue app.  The default profile remains Classic (`BSB002`).
Bridge Pro behaviour is selected only with `BRIDGE_PROFILE=pro` or
`--bridge-profile pro`.

## Scope and compatibility

| Surface | Status |
| --- | --- |
| Classic identity and discovery | Regression-tested; default unchanged |
| Opt-in Pro identity, HTTPS mDNS policy and V2 product data | Regression-tested |
| Motion-area resource graph, persistence and V2 mutations | Synthetic integration-tested |
| SSE multi-client ordering, resume and restart cursor recovery | Synthetic integration-tested |
| Motion-area behaviour dispatch and delayed no-motion cancellation | Synthetic integration-tested |
| Native Zigbee2MQTT `blink` identify / alert fallback | Unit-tested |
| Radio-based MotionAware detection | Not implemented: Zigbee2MQTT `linkquality` is not accepted as a motion measurement |
| Official Hue app discovery, pairing and MotionAware UI | Untested; do not describe as supported |

## Isolated API test

Use only a fresh directory and a disposable Docker state volume.  Never mount
an existing diyHue configuration, certificate, Zigbee2MQTT data directory, or
production Docker volume.

```sh
git rev-parse HEAD
docker compose -f examples/docker-compose/motionaware-beta/docker-compose.yml up --build
docker compose -f examples/docker-compose/motionaware-beta/docker-compose.yml exec bridge \
  curl --fail http://127.0.0.1:80/api/config
```

The compose file uses TEST-NET addressing and an internal Docker network, so
it is intentionally not discoverable by a phone or a real Hue app.  Its
generated `state/` directory is ignored by Git.  Stop it with:

```sh
docker compose -f examples/docker-compose/motionaware-beta/docker-compose.yml down
```

## Migration and rollback

1. Stop the separate beta container.
2. Copy its disposable state directory as a rollback artifact.
3. Set `BRIDGE_PROFILE=pro` only for that beta instance and start it.
4. To roll back, stop the beta, restore its copied state directory, set
   `BRIDGE_PROFILE=classic` (or remove it), and start that beta container.

The profile setting is persisted in that instance's `config.yaml`; it does not
rewrite a Classic bridge unless its own configuration volume is reused.  Do not
reuse that volume.

## Test commands

```sh
python3 -m py_compile BridgeEmulator/flaskUI/v2restapi.py \
  BridgeEmulator/functions/motionAware.py BridgeEmulator/services/eventStreamer.py
python3 -m unittest discover -v tests
docker build --platform=linux/arm64 -t diyhue/core:motionaware-beta -f .build/Dockerfile .
```

## Official Hue app acceptance procedure

Run this only after the isolated image and test suite pass, with a separate
Pro test instance and documented rollback artifacts.  Do not change the
Classic instance or pair/reset/migrate Zigbee devices.

1. Confirm the app discovers the test bridge over its intended network path.
2. Pair using the normal physical-link-button flow; do not bypass TLS or app
   trust checks.
3. Confirm the app identifies the bridge as Pro and record the exact model,
   firmware/API strings it displays.
4. Confirm whether MotionAware is visible.  If so, create an area, select
   participants, adjust sensitivity, and configure a scene.
5. Record the first failing step, a sanitized request/response trace, and
   whether it is discovery, TLS, pairing, capability discovery, resource
   validation, SSE, or runtime behaviour.
6. Test motion and no-motion with recorded, reproducible physical traces.
   Include false positives/negatives, latency, cooldown and manual-off cases.

No result from this repository's synthetic tests counts as a Hue-app or
radio-detection result.

## Privacy-safe bug report template

```text
Source commit:
Container image digest:
Profile: classic | pro
Architecture:
Test type: unit | isolated API | simulated MQTT | hardware | Hue app
First failing acceptance step:
Expected / actual result:
Sanitized V2 resource and SSE payloads:
Motion trace summary (sample rate, duration, sensitivity, false +/-):
Rollback completed: yes | no

Do not include application keys, certificates, private keys, bridge IDs,
public/private IP addresses, MAC addresses, Wi-Fi/Zigbee credentials, or
unredacted device names.
```
