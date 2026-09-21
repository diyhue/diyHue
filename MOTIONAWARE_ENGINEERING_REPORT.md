# MotionAware integration reconnaissance

Base inspected: `upstream/dev` at `e5b5c0b1e8dbd9ad4402ab2bb1249eeb9410279c`.

## Current branch relationship

`#1120`, `#1127`, and `#1128` are merged. `#1121` is open. `#1122` through
`#1126` are draft commits arranged as one cumulative stack; each contains old
copies of previously merged configuration/profile changes. `#1108`, `#1109`,
and `#1118` are merged. `#1118` is server-side pairing to an external physical
Hue bridge, not Bridge Pro emulation, and is not used as evidence of Pro app
compatibility.

## Findings

The original stack advertised every diyHue light as a MotionAware candidate and
attempted to poll Zigbee2MQTT `linkquality` every two seconds. `linkquality` is
a link/routing metric, not an exposed radio-presence measurement; it has no
validated calibration, sampling contract, resolution guarantee, or measured
false-positive/negative performance. The polling implementation is therefore
excluded from this candidate.

The V2 resource work had useful foundations but needed integration with the
current profile surfaces and required full-resource SSE updates. The event
stream also accepted a pre-restart `Last-Event-ID` unchanged, which could
permanently suppress new events after its process-local sequence restarted.

## Verified in this candidate

The candidate has an opt-in Pro profile; MotionAware resource serialization,
create/update/delete persistence, behaviour dispatch, native identify fallback,
and bounded/resumable SSE have automated coverage. Candidate eligibility now
requires an explicit adapter capability flag and does not treat ordinary
Zigbee2MQTT lights as RF-capable.

## Unverified / blocked

No official Hue app action or experimental Pro deployment was performed from
this worktree. Consequently there is no observed app failure step and no
claim that app TLS trust, pairing, capability gating, MotionAware UI, or RF
detection works. The next engineering prerequisite is a supported adapter that
can provide documented, calibrated radio measurements plus hardware traces;
only then can a light be safely marked as an eligible candidate.
