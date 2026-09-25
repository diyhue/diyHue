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
