"""Finite reducer stimuli, not a production scheduler or display measurement."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import heapq
import json
import math
from pathlib import Path
import random
import statistics
import sys
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'BridgeEmulator'))
from services.haReflection import Reflector, translate

SCHEDULING_DISCLAIMER = (
    'Custom reducer stimuli, not production scheduler efficiency: absolute periodic '
    'ticks, an injected 30s overlap read, and queued retries surviving intervening '
    'successes. Counts are dispatched fixture stimulus requests, not HA load.')


def nearest_rank_p95(samples):
    ordered = sorted(samples)
    return ordered[math.ceil(len(ordered) * .95) - 1] if ordered else None


def row(n, at):
    return {'entity_id': 'light.synthetic', 'state': 'on',
            'attributes': {'diyhue': 'include', 'brightness': n},
            'last_updated': (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=at)).isoformat()}


def fixture():
    light = SimpleNamespace(protocol='homeassistant_ws', protocol_cfg={'entity_id': 'light.synthetic'},
                            state={'on': False, 'bri': 0, 'reachable': True})
    reducer = Reflector({'1': light}, lambda state: state is not None)
    epoch = reducer.new_session()
    reducer.snapshot(epoch, reducer.begin_snapshot(epoch), [row(0, 0)])
    return light, reducer, epoch


def workload():
    rng = random.Random(153)
    times = [2 + i * 2.3 + rng.random() for i in range(48)]
    times += [30 + i * .004 for i in range(20)]
    return sorted(at for at in times if not 80 <= at < 83)


def replay(period, events, audit=None):
    light, reducer, epoch = fixture()
    shadow_light, shadow, shadow_epoch = fixture()
    queue, serial = [], 0

    def schedule(at, kind, payload=None):
        nonlocal serial
        serial += 1
        heapq.heappush(queue, (at, serial, kind, payload))

    def record(kind, **values):
        if audit is not None:
            audit.append(dict(kind=kind, at=now, **deepcopy(values)))

    changes = {}
    for n, at in enumerate(workload(), 1):
        changes[n] = (at, row(n, at))
        schedule(at, 'source', n)
    schedule(80, 'remove')
    schedule(83, 'restore')
    schedule(60, 'disconnect')
    schedule(63, 'reconnect')
    schedule(30, 'poll')
    for tick in range(0, 121, period):
        schedule(tick, 'poll')
    source, source_cut, shadow_cut = row(0, 0), 0, 0
    inflight, connected, reconnect_baseline = None, True, False
    matched, samples, requests, errors, decreases = set(), [], 0, 0, 0
    dropped, last_revision, initial_equal, post_equal, pending = 0, '', 0, 0, 0
    dropped_ids, repaired_ids = set(), set()
    removed_fences, stale_fenced = 0, 0
    lifecycle = {'remove': {'started_at': 80, 'observed_at': None, 'latency_ms': None},
                 'restore': {'started_at': 83, 'observed_at': None, 'latency_ms': None}}
    while queue:
        now, _, kind, payload = heapq.heappop(queue)
        if now > 121:
            break
        if kind == 'source':
            source_cut = payload
            source = deepcopy(changes[payload][1])
            record('source', cut=source_cut)
            if events and connected:
                if payload % 17 == 0:
                    dropped += 1
                    dropped_ids.add(payload)
                else:
                    schedule(now + (.7 if payload % 19 == 0 else .020), 'event',
                             (epoch, shadow_epoch, source_cut, deepcopy(source)))
        elif kind == 'event':
            callback_epoch, callback_shadow_epoch, cut, candidate = payload
            before = deepcopy((reducer.rows, light.state, reducer.pending, reducer.ready,
                               shadow.rows, shadow_light.state, shadow.pending, shadow.ready))
            reducer.event(callback_epoch, 'light.synthetic', candidate)
            shadow.event(callback_shadow_epoch, 'light.synthetic', candidate)
            if callback_epoch != epoch:
                after = (reducer.rows, light.state, reducer.pending, reducer.ready,
                         shadow.rows, shadow_light.state, shadow.pending, shadow.ready)
                assert before == after
                stale_fenced += 1
                record('stale_callback', callback_epoch=callback_epoch, epoch=epoch, unchanged=True)
            else:
                if shadow.ready and shadow.rows.get('light.synthetic') == candidate:
                    shadow_cut = cut
                if reducer.needs_sync and inflight is None and connected:
                    schedule(now + 2, 'poll')
        elif kind in ('remove', 'restore'):
            source = None if kind == 'remove' else row(200, now)
            source_cut = kind
            if events and connected:
                reducer.event(epoch, 'light.synthetic', source)
                shadow.event(shadow_epoch, 'light.synthetic', source)
                if shadow.ready and shadow.rows.get('light.synthetic') == source:
                    shadow_cut = source_cut
                if kind == 'remove':
                    assert not reducer.command_allowed(light)
                    removed_fences += 1
                schedule(now + 2, 'poll')
        elif kind == 'disconnect':
            connected = False
            # Deliberately deliver an old callback after the reconnect baseline.
            if events:
                schedule(63.1, 'event', (epoch, shadow_epoch, source_cut, deepcopy(source)))
            reducer.disconnect(epoch)
            shadow.disconnect(shadow_epoch)
            record('disconnect', reachable=light.state['reachable'])
            epoch = reducer.new_session()
            shadow_epoch = shadow.new_session()
            shadow_cut = None
            inflight = None
        elif kind == 'reconnect':
            connected = True
            reconnect_baseline = True
            schedule(now, 'poll')
        elif kind == 'poll' and connected and inflight is None:
            ticket = reducer.begin_snapshot(epoch)
            shadow_ticket = shadow.begin_snapshot(shadow_epoch) if reconnect_baseline else None
            inflight = (epoch, ticket)
            requests += 1
            record('fixture_request', epoch=epoch)
            expected = None if source is None else translate(light.state, source)
            schedule(now + .05, 'result', (epoch, ticket, deepcopy(source), source_cut,
                                          expected, shadow_ticket))
        elif kind == 'result':
            captured_epoch, ticket, captured, cut, expected, shadow_ticket = payload
            if inflight == (captured_epoch, ticket):
                inflight = None
            # Fixture cut provenance comes from consumed callbacks, never inferred
            # from equal values or updated by reconciliation before comparison.
            equal = (connected and captured_epoch == epoch and shadow.ready and shadow_cut == cut
                     and shadow.rows.get('light.synthetic') == captured
                     and (shadow_light.state == expected if captured is not None
                          else not shadow_light.state['reachable']))
            record('comparison', cut=cut, consumed_cut=shadow_cut, ready=shadow.ready, equal=equal)
            if equal:
                if cut == 0:
                    initial_equal += 1
                else:
                    post_equal += 1
            else:
                pending += 1
            ok = reducer.snapshot(captured_epoch, ticket, [] if captured is None else [captured])
            if not ok:
                errors += 1
                if connected:
                    schedule(now + 2, 'poll')
            elif (events and reconnect_baseline and captured_epoch == epoch
                  and shadow_ticket is not None):
                if shadow.snapshot(shadow_epoch, shadow_ticket, [] if captured is None else [captured]):
                    reconnect_baseline = False
                    shadow_cut = cut
                    record('shadow_seed', epoch=shadow_epoch, cut=cut)
        current = reducer.rows.get('light.synthetic')
        stamp = current['last_updated'] if current is not None else ''
        if stamp and last_revision and stamp < last_revision:
            decreases += 1
        if stamp:
            last_revision = stamp
        # Lifecycle coverage measures membership/availability, separately from
        # exact brightness matches; restoration may carry a newer source value.
        removed = current is None and not light.state['reachable'] and not reducer.command_allowed(light)
        restored = (current is not None and light.state['reachable'] and reducer.command_allowed(light)
                    and current['last_updated'] >= row(200, 83)['last_updated'])
        for transition, observed in [('remove', removed), ('restore', restored)]:
            observation = lifecycle[transition]
            if (now >= observation['started_at'] and observation['observed_at'] is None and observed
                    and (transition != 'remove' or now < 83)):
                observation['observed_at'] = now
                observation['latency_ms'] = round((now - observation['started_at']) * 1000, 3)
        for n, (started, candidate) in changes.items():
            if n not in matched and current == candidate:
                assert light.state == translate(light.state, candidate)
                matched.add(n)
                if kind == 'result' and n in dropped_ids:
                    repaired_ids.add(n)
                samples.append(now - started)
    lifecycle_matches = sum(item['observed_at'] is not None for item in lifecycle.values())
    p95 = nearest_rank_p95(samples)
    return {'brightness_changes': len(changes), 'matched': len(matched),
            'missed_or_coalesced': len(changes)-len(matched), 'dropped_events': dropped,
            'dropped_events_repaired_by_poll': len(repaired_ids),
            'mean_ms': round(statistics.mean(samples)*1000, 3) if samples else None,
            'p95_ms': round(p95*1000, 3) if p95 is not None else None,
            'percentile_method': 'nearest-rank ceil(0.95 * matched_count); matching brightness samples only',
            'max_ms': round(max(samples)*1000, 3) if samples else None,
            'fixture_stimulus_requests': requests, 'scheduling_disclaimer': SCHEDULING_DISCLAIMER,
            'rejected_or_fenced_snapshots': errors, 'row_revision_decreases': decreases,
            'removal_fence_checks': removed_fences, 'stale_epoch_callbacks_fenced': stale_fenced,
            'initial_cut_equalities': initial_equal, 'post_change_cut_equalities': post_equal,
            'unproven_cut_comparisons': pending,
            'lifecycle': {'expected': 2, 'matched': lifecycle_matches, 'missed': 2-lifecycle_matches,
                          'definition': 'removal: unreachable tombstone and command fence; restoration: '
                                        'authoritative available membership at or after restore revision',
                          'observations': lifecycle}}


if __name__ == '__main__':
    results = {'kind': 'synthetic discrete-event reducer/cache replay; NOT display measurements',
               'assumptions': '20ms event / 50ms read; deterministic drop/reorder/burst/reconnect/removal; '
                              'brightness paused during removal; explicit old-epoch callback',
               'runtime_global_parity': 'INCONCLUSIVE: HA supplies no global inventory cut',
               'poll_10s': replay(10, False), 'poll_2s': replay(2, False),
               'events_with_60s_repair': replay(60, True)}
    assert all(results[k]['row_revision_decreases'] == 0
               for k in ('poll_10s', 'poll_2s', 'events_with_60s_repair'))
    assert results['events_with_60s_repair']['rejected_or_fenced_snapshots'] > 0
    assert results['events_with_60s_repair']['dropped_events_repaired_by_poll'] > 0
    assert results['events_with_60s_repair']['stale_epoch_callbacks_fenced'] > 0
    print(json.dumps(results, indent=2))
