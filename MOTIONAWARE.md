# Bridge Pro MotionAware foundation

MotionAware is available only with the explicit Bridge Pro profile (`BSB003`).

This implementation provides the V2 resource, persistence, event and behavior
runtime required for MotionAware development. It intentionally does not
implement physical RF motion detection.

## Provider contract

A compatible adapter/provider must:

1. mark only verified devices with `motion_aware_candidate = true`;
2. detect physical motion using its own validated telemetry;
3. publish boolean transitions through:

`setMotionAwareRuntimeMotion(area_id, value, source="provider-name")`

Runtime motion state is transient and is never persisted.

Zigbee2MQTT `linkquality` is a routing/link metric and is explicitly not
treated as MotionAware telemetry.

Classic (`BSB002`) remains unchanged and does not expose MotionAware.

## Explicit development candidates

Until a protocol/provider implements validated MotionAware telemetry,
individual light devices can be exposed explicitly as MotionAware candidates
for development and Hue-client compatibility testing:

```yaml
motion_aware:
  candidate_devices:
    - "<v2-device-id>"
```

The ID is the V2 `device.id`, not the legacy light ID.

This allowlist only exposes the reference-only `motion_area_candidate`
service. It does not synthesize RF motion, does not interpret Zigbee2MQTT
`linkquality`, and does not make an unsupported device physically
MotionAware-capable.

A real provider may instead set `motion_aware_candidate = true` in its device
protocol configuration and publish validated transitions through
`setMotionAwareRuntimeMotion(...)`.
