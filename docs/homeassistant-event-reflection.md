# Experimental Home Assistant event reflection (DRAFT, off by default)

This is an opt-in review candidate for reflecting **already configured**
`homeassistant_ws` Hue lights directly into the cache served by Hue v1. It has
not been deployed, tested against a live Home Assistant instance, or qualified
with a Brilliant panel. Keep the flag off until the gaps below are resolved and
an operator has approved load/compatibility/benefit criteria. No physical
actuation or displayed latency improvement is established by this change.

## Configuration and rollback

Existing installations keep their legacy path unless the Home Assistant config
contains `homeAssistantEventReflection: true`. The opt-in additionally requires
`homeAssistantUseHttps: true`, the existing `homeAssistantIp`,
`homeAssistantPort`, and a separate `homeAssistantToken`. An optional
`homeAssistantCaFile` names a trusted PEM CA bundle; otherwise use the system CA
file or certifi bundle. ws4py >= 0.6.0 supplies the websocket parser/reader; the opt-in
upgrade uses a standard verified SSLContext with hostname checking. Plaintext opt-in is rejected before a connection attempt.
Never put an HA access token in Hue client credentials or public artifacts.
Restrict the existing config file to the service account. The inbound Hue auth
contract is unchanged. CA context tests verify trust-store loading, mandatory
chain verification and hostname checking; they do not constitute live certificate
rotation/revocation qualification or an actual certificate rejection handshake.

Changing the configured outbound token/host/port/CA path replaces the session
and fences callbacks/results from the old epoch. A replacement must authenticate,
subscribe successfully, and finish a complete `get_states` baseline before
commands are permitted. CA file content changes are read on reconnect, and do
not independently trigger a reconnect. A direct `create_ws_client` reconfigure
stops/fences the previous event supervisor. A global ownership lock serializes
concurrent replacements; old ownership remains published until retirement drains.
The prior legacy transport is closed when entering event mode, so toggles cannot
leave old subscriptions alive. Worker disable releases its lifecycle lock before
acquiring global ownership, preventing inverse lock ordering. Setting the flag false fences/closes
the event session and restores the legacy connection and stateFetch path. Check
that the legacy authoritative cache and client behavior have converged before
calling rollback complete. Invalid HA credentials can prevent legacy recovery
as well. Credential leak discovery, revocation ownership/time, and operational
rotation remain unqualified.

## Cache ownership and ordering

One reducer lock serializes event and full-read candidates and command checks.
The general stateFetch loop skips HA lights only while the opt-in session owns
them, preventing stale cached HA reads from becoming another writer. Other
protocols retain their existing behavior. Commands preserve the existing
optimistic write semantics, under the same lock. Cache state is not physical
confirmation. Removed, excluded, unbaselined, replaced, or detached mappings
cannot pass the Light pre-mutation guard or the protocol dispatch guard. Direct
v1 state PUT returns a Hue error type 901 for an unavailable mapping.

The reader subscribes before requesting a baseline and waits for a successful
subscription acknowledgment (including `result: null`). It then accepts only
complete valid `get_states` lists; `[]` is a complete empty list, while missing,
malformed or failed responses never delete membership. Snapshot tokens and
session epochs reject old completions. Per-entity timezone-aware `last_updated`
values prevent an older value from replacing a newer event. Equal timestamps
with unequal payloads request reconciliation. Deletion/exclusion and
recreation inside one in-flight read are ambiguous and reject that entire read.
There is no local-arrival-time tie-breaker. A deletion cannot be restored by an
event; restoration requires a later authoritative complete read. Malformed
translation data rejects the entire baseline before any cache mutation.

`unavailable`/`unknown` preserve last-known `on`/brightness/color and set
`reachable: false`; neither invents `off`. This candidate intentionally retains
the existing Hue object for a removed/excluded entity as an unreachable,
command-blocked tombstone. **It does not implement served-object deletion** as
proposed in the broader contract. In-memory tombstones/rows/pending candidates
are restricted to current configured mappings, with retired mappings pruned on
reconcile. Pending events coalesce per mapping and preserve deletion ambiguity.
The cap is 4096 configured mappings/candidates; overflow requires reconciliation
and suppresses event mode. `get_states` itself still returns HA's entire inventory
and transport/frame memory is not a streaming bounded parser.

## Fixed candidate recovery budgets (not measured safe defaults)

- One supervisor, one connection, and one outstanding full read.
- Full `get_states` every 60 seconds permanently, independent of Hue clients.
- 15-second socket/read/auth/subscription deadline; socket writes also retain
  a finite timeout, restored after ws4py reader startup resets blocking mode.
  TLS/HTTP upgrade network I/O has a total 15-second monotonic deadline and a
  16 KiB header cap; slow-drip responses cannot extend it. HA ping requests every
  5 seconds maintain quiet connections. **Deployment blocker:** OS hostname
  resolution can occur both in the websocket constructor and again inside
  `socket.connect`; the deadline cannot interrupt the OS resolver. Thus total
  connection setup and retirement/reconfiguration can wait for the resolver,
  exceeding 15 seconds. Resolve and qualify this gap before any deployment.
- Failed/ambiguous full reads retry no faster than every 2 seconds; three
  consecutive failed reads close the session and require a new baseline.
- Reconnect backoff is 2, 4, 8, 16, then 32 seconds, plus 0-1 second jitter.
  An invalid configuration uses bounded 2-second worker checks and cannot connect.
- At most 256 outstanding protocol request IDs before dispatch is rejected or
  reconnect requested. The single reader's successful replies retire IDs.

A quiet state stream is not a failure signal. Socket read failure or a deadline
forces recovery; periodic authoritative reads repair dropped state events even
when pongs continue. Ping liveness does not claim delivery completeness. These
bounds are implementation choices for offline review; permitted HA load,
reconnect-storm behavior and production tuning require separate qualification.
No individual Hue cache miss performs an HA read. Discovery shares the same
single-flight full read.

## Explicit qualification gaps

This is **not full fulfillment of the broader event-reflection proposal**:

- Full inventory/registry discovery, object creation/deletion, mapping updates
  and capability remapping are not implemented. Configure/discover mappings
  first using the legacy path. This candidate qualifies only existing mappings.
- HA provides no global inventory/registry snapshot revision in `get_states`.
  Per-value timestamp guards are conservative runtime safety checks, not proof
  of a source-wide parity cut. Same-cut shadow parity is **INCONCLUSIVE**.
- Continuous ambiguous overlaps can keep the candidate in recovery. The cache
  retains its last known values, and commands require an established baseline.
- Attribute validation/translation covers the existing on/off, brightness,
  color temperature, XY and HS fields; model capabilities and every HA provider's
  attribute semantics still need an inventory-specific compatibility review.
- Live auth rotation/revocation, OS resolver stalls, failed trust/hostname handshakes, measured HA
  request load, source timestamp skew/regression, client/group/scene compatibility,
  and accepted recurrence windows remain unqualified.
- No panel poll cadence, native panel display, physical light, production
  endpoint, or Brilliant runtime was accessed by the tests or benchmark.

## Reproducible offline evidence

Use a separate uv environment, never system pip:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python examples/benchmark_ha_reflection.py
```

TDD record: the first `test_ha_reflection.py` run failed at import with
`ModuleNotFoundError: services.haReflection`; after implementing the reducer,
all initial nine reducer cases passed. Subsequent adapter and regression tests
exercise the actual callback/session code, verified SSLContext construction, real ws4py reader startup after its blocking reset,
bounded slow-drip/oversized upgrade, legacy/event toggles, concurrent replacement,
Light guard before optimistic mutation, and v1 REST error behavior.

The benchmark executes the production reducer/translation through a finite
`heapq` discrete-event replay. The workload has 68 source changes (including a
20-change burst), deterministic 20 ms event delivery / 50 ms full-read service
assumptions, dropped and delayed events, a full-read/burst overlap, disconnect /
reconnect baseline, removal and restoration. First matching cache times are
observed after real reducer operations; no commit timestamp is precomputed.
The fixture supplies independent atomic source cut identifiers so an event-only
shadow can be compared before authoritative reconciliation overwrites the main
lane. That proves only replay same-cut value parity for this static mapping;
HA runtime inventory-wide parity stays **INCONCLUSIVE**.

Recorded replay (conditional synthetic assumptions):

| Mode | Matched / 68 | Missed or coalesced | Mean / p95 / max ms among matches | Full reads |
|---|---|---|---|---|
| 10 s polls | 11 | 57 | 1587.531 / 1536.592 / 9486.304 | 13 |
| 2 s polls | 46 | 22 | 945.736 / 1874.721 / 1983.846 | 60 |
| Events + 60 s floor | 64 | 4 | 226.276 / 700 / 9486.304 | 9 |

These distributions are conditional on matching samples and must be read with
the missed/coalesced counts; superseded changes cannot be assigned zero latency.
The event replay drops four events; two are later matched through real poll
repair and two are superseded. One overlapping snapshot is rejected. No served
source revision regresses. The main event lane checks the removal command fence.
Two event-shadow comparisons establish equal fixture cuts; seven have unproven
cuts and are reported separately, never converted into PASS. Comparator lanes
also run the same disconnect/removal workload and source snapshots.

These synthetic numbers expose scheduling, loss and recovery effects in the
actual reducer. They exclude real CPU/network delays, production HA load and
panel polling. No physical light or display improvement is measured.
