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
with unequal entity/state/attributes request reconciliation. Independently changing
report/context metadata does not conflict with an unchanged state revision. Deletion/exclusion and
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
The cap is 4096 distinct configured entity mappings/candidates. Overflow fences
event publication and command authority immediately on admission/read/command
checks, and a new baseline is required after returning below the cap. `get_states` itself still returns HA's entire inventory
and transport/frame memory is not a streaming bounded parser.

## Fixed candidate recovery budgets (not measured safe defaults)

- One supervisor, one connection, and one outstanding full read.
- Full `get_states` every 60 seconds permanently, independent of Hue clients.
- 15-second socket/read/auth/subscription deadline; socket writes also retain
  a finite timeout, restored after ws4py reader startup resets blocking mode.
  TLS/HTTP upgrade network I/O has a total 15-second monotonic deadline and a
  16 KiB header cap; slow-drip responses cannot extend it. HA ping requests every
  5 seconds maintain quiet connections. Hostname resolution runs in one child
  process using the remaining connection-attempt budget; a stalled child is
  killed and reaped. ws4py construction uses a numeric bootstrap address and
  TCP connects to the resolved numeric tuple, avoiding another OS lookup. The
  original hostname remains the HTTP Host and TLS SNI/verification identity.
  Numeric IPv4/IPv6 configuration needs no resolver child. Resolution and network
  I/O share one absolute 15-second attempt deadline; process scheduling,
  interpreter launch and cleanup are not hard real-time bounds. Retry backoff
  starts after failed-attempt cleanup, so slow attempts cannot consume the pause.
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
- Live auth rotation/revocation, failed trust/hostname handshakes, measured HA
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
Light guard before optimistic mutation, and v1 REST error behavior. Resolver tests
exercise actual stalled-child termination/reaping and numeric-only parent address
construction while preserving the configured TLS hostname.

The benchmark executes the production reducer/translation through a finite
`heapq` discrete-event replay. The workload has 67 brightness changes (including
a 20-change burst), deterministic 20 ms event delivery / 50 ms full-read service
assumptions, dropped/delayed events, an injected read/burst overlap, reconnect,
removal and restoration. Brightness changes pause during the explicit absence.
First matching cache times are observed after real reducer operations.

This is a **custom reducer stimulus experiment**. Absolute periodic ticks,
queued retries and an injected overlap read differ from the production
supervisor's mutable `next_read` scheduling. `fixture_stimulus_requests` counts
dispatched fixture operations, not production HA reads or scheduling efficiency.
These counts cannot establish HA load or a safe polling comparator.

The event-only shadow is seeded at initialization and explicit reconnect
baselines only. Comparisons record an independently consumed fixture cut and
require a ready shadow. Initial-cut equalities are separate from post-change
comparisons. The fixture provides source cuts for one static mapping; it does
not establish HA runtime inventory-wide parity, which remains **INCONCLUSIVE**.
Seven event-lane comparisons have unproven cuts and no qualification deadline;
they are reported without a PASS claim.

Recorded replay under the declared synthetic assumptions:

| Mode | Brightness matched / 67 | Missed/coalesced | Mean / p95 / max ms among matches | Fixture requests |
|---|---|---|---|---|
| 10 s stimuli | 11 | 56 | 1587.531 / 9486.304 / 9486.304 | 13 |
| 2 s stimuli | 45 | 22 | 938.522 / 1954.331 / 1983.846 | 60 |
| Event stimuli + 60 s repair floor | 63 | 4 | 89.340 / 700 / 1903.448 | 9 |

p95 uses nearest-rank `ceil(0.95 * matched_count)`. These distributions cover only
matching brightness samples and must be read with missing/coalesced counts;
superseded or unseen changes are not assigned zero latency. The event fixture
intentionally drops three connected events; one later matches via poll repair
and two are superseded. One overlapping snapshot is rejected. No extant row's
source revision decreases. This metric alone does not prove all cache fields,
availability or mapping correctness.

Separate lifecycle accounting observes both expected transitions in each lane:
removal requires unreachable tombstone plus command rejection; restoration
requires authoritative available membership at or after the explicit restore
revision. Synthetic removal/restoration times are 50/7050 ms for 10 s stimuli,
50/1050 ms for 2 s stimuli, and 0/2050 ms for event stimuli. Reconnect uses the
real reducer disconnect mutation and a new session; an explicitly delayed old-
epoch callback is fenced. The event shadow reports one initial-cut equality,
one post-change equal-cut observation (the removal/tombstone cut, not brightness
parity) and seven unproven comparisons. These are narrow fixture observations,
not complete proposal-comparator qualification.

The regression suite covers percentile small samples, fixture-scheduling labels,
shadow reseeding/cut readiness, lifecycle accounting, absence stability,
disconnect reachability and old-epoch callbacks. These synthetic observations
exclude real CPU/network delays, production HA load and panel polling. No
physical light or native display improvement is measured.
