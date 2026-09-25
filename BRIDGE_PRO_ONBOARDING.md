# Bridge Pro onboarding and Classic-to-Pro transition

Bridge Pro support remains experimental and opt-in.

The strongest validated path is now a **Classic-first transition**: an
application registers normally while diyHue is BSB002, the same persisted
bridge identity and API users are then restarted with `BRIDGE_PROFILE=pro`,
and the existing application credential continues to authenticate the BSB003
bridge.

Fresh **local protocol onboarding** of a never-before-paired BSB003 bridge is
also validated. Fresh onboarding through the stock Hue app itself remains
experimental and is not claimed here.

## Validated transition

The validated transition preserves:

- the existing bridge id;
- the persisted API-user whitelist;
- the V1 registration username used as the V2 `hue-application-key`.

After transition the bridge advertises as BSB003 over `_hue._tcp.local.` on
HTTPS port 443 and does not advertise Classic SSDP.

The DTLS `clientkey` remains a separate credential and is not accepted as the
V2 application key.

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

## Fresh BSB003 protocol validation

A separate isolated test also validated onboarding from completely empty
Bridge Pro state without relying on a previous Classic registration.

The bridge started directly as BSB003 with an empty configuration volume.

The normal local pairing lifecycle succeeded:

1. BSB003 identity was active before registration.
2. The local link-button window was opened through the normal virtual-button
   mechanism.
3. `POST /api/` created a new application username and DTLS client key.
4. The application username authenticated successfully on `/auth/v1`.
5. The same username authenticated `GET /clip/v2/resource/bridge`.
6. The DTLS `clientkey` was rejected as a V2 application key.
7. After a real container restart the newly created API user was restored from
   persisted configuration.
8. `/auth/v1` and `/clip/v2/resource/bridge` continued to return HTTP 200.

This demonstrates that diyHue's local BSB003 registration, persistence and V2
authentication path works from fresh state. It does not by itself demonstrate
that the stock Hue app will complete its fresh Bridge Pro ownership/onboarding
flow.

## Stock Hue app validation

A live Classic-to-Pro transition was validated with the stock Hue iOS app on
2026-09-24.

The test started from an existing BSB002 registration, cloned the same
persisted bridge state, and restarted that identity as BSB003 with HTTPS
discovery on port 443.

Observed from the stock app after the transition:

- `_hue._tcp` discovery of the BSB003 bridge;
- HTTPS connections to port 443, with no use of the Classic HTTP port 80;
- reuse of the previously persisted Hue application credential;
- authenticated V1 configuration requests returning HTTP 200;
- `GET /clip/v2/resource/bridge` returning HTTP 200;
- `GET /clip/v2/resource` returning HTTP 200;
- `GET /eventstream/clip/v2` returning HTTP 200;
- V2 write requests from the app returning HTTP 200.

A temporary diagnostic trace matched the incoming `hue-application-key`
against the application username already stored before the transition. No new
pairing was required for this validation.

This validates stock-app credential continuity across the BSB002-to-BSB003
transition. It does **not** prove fresh/direct onboarding of an unpaired BSB003
bridge.

## Still not validated

The following remain outside this result:

- fresh official Hue-app onboarding directly to an unpaired BSB003 instance;
- QR/setup-code ownership enrolment;
- Philips account/cloud registration behavior;
- equivalence to Philips hardware certificate provisioning;
- MotionAware UI visibility in the stock Hue app;
- physical Bridge Pro radio sensing.

No Philips-issued or forged certificate is used or claimed.
