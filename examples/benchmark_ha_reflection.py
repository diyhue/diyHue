"""Deterministic discrete-event replay of the real reducer; no network or panels."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import heapq
import json
from pathlib import Path
import random
import statistics
import sys
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'BridgeEmulator'))
from services.haReflection import Reflector, translate


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
    return sorted(times)


def replay(period, events):
    light, reducer, epoch = fixture()
    shadow_light, shadow, shadow_epoch = fixture()
    queue, serial = [], 0
    def schedule(at, kind, payload=None):
        nonlocal serial
        serial += 1
        heapq.heappush(queue, (at, serial, kind, payload))
    changes = {}
    for n, at in enumerate(workload(), 1):
        changes[n] = (at, row(n, at))
        schedule(at, 'source', n)
    # Explicit deletion and authoritative restoration in otherwise identical trials.
    schedule(80, 'remove')
    schedule(83, 'restore')
    schedule(60, 'disconnect')
    schedule(63, 'reconnect')
    schedule(30, 'poll')  # An in-flight authoritative read overlaps the burst.
    for tick in range(0, 121, period):
        schedule(tick, 'poll')
    source, source_cut = row(0, 0), 0
    inflight, connected = None, True
    matched, samples, reads, errors, regressions = set(), [], 0, 0, 0
    dropped, last_revision, shadow_pass, shadow_pending = 0, '', 0, 0
    dropped_ids, repaired_ids = set(), set()
    removed_fences = 0
    while queue:
        now, _, kind, payload = heapq.heappop(queue)
        if now > 121:
            break
        if kind == 'source':
            source_cut = payload
            source = deepcopy(changes[payload][1])
            if events and connected:
                if payload % 17 == 0:
                    dropped += 1
                    dropped_ids.add(payload)
                else:
                    schedule(now + (.7 if payload % 19 == 0 else .020), 'event', deepcopy(source))
        elif kind == 'event' and connected:
            reducer.event(epoch, 'light.synthetic', payload)
            shadow.event(shadow_epoch, 'light.synthetic', payload)
            if reducer.needs_sync and inflight is None:
                schedule(now + 2, 'poll')
        elif kind in ('remove', 'restore'):
            source = None if kind == 'remove' else row(200, now)
            source_cut = kind
            if events and connected:
                reducer.event(epoch, 'light.synthetic', source)
                shadow.event(shadow_epoch, 'light.synthetic', source)
                if kind == 'remove':
                    assert not reducer.command_allowed(light)
                    removed_fences += 1
                schedule(now + 2, 'poll')
        elif kind == 'disconnect':
            connected = False
            epoch = reducer.new_session()
            shadow_epoch = shadow.new_session()
            inflight = None
        elif kind == 'reconnect':
            connected = True
            schedule(now, 'poll')
        elif kind == 'poll' and connected and inflight is None:
            ticket = reducer.begin_snapshot(epoch)
            inflight = (epoch, ticket)
            reads += 1
            # Replay barrier: source_cut and canonical source state are captured
            # atomically by the fixture, independently of either reducer.
            expected = None if source is None else translate(light.state, source)
            schedule(now + .05, 'result', (epoch, ticket, deepcopy(source), source_cut, expected))
        elif kind == 'result':
            captured_epoch, ticket, captured, cut, expected = payload
            if inflight == (captured_epoch, ticket):
                inflight = None
            # Compare independently event-derived candidates before authoritative
            # reconciliation can overwrite either lane. Unknown cuts stay pending.
            shadow_row = shadow.rows.get('light.synthetic')
            if captured is not None and shadow_row == captured:
                assert shadow_light.state == expected
                shadow_pass += 1
            else:
                shadow_pending += 1
            ok = reducer.snapshot(captured_epoch, ticket, [] if captured is None else [captured])
            if not ok:
                errors += 1
                if connected:
                    schedule(now + 2, 'poll')
            elif events and not shadow.ready:
                # Only reconnect baselines enter the otherwise event-only shadow.
                shadow.snapshot(shadow_epoch, shadow.begin_snapshot(shadow_epoch), [] if captured is None else [captured])
        current = reducer.rows.get('light.synthetic')
        stamp = current['last_updated'] if current is not None else ''
        if stamp and last_revision and stamp < last_revision:
            regressions += 1
        if stamp:
            last_revision = stamp
        for n, (started, candidate) in changes.items():
            if n not in matched and current == candidate:
                expected = translate(light.state, candidate)
                assert light.state == expected
                matched.add(n)
                if kind == 'result' and n in dropped_ids:
                    repaired_ids.add(n)
                samples.append(now - started)
    ordered = sorted(samples)
    return {'source_changes': len(changes), 'matched': len(matched),
            'missed_or_coalesced': len(changes)-len(matched), 'dropped_events': dropped,
            'dropped_events_repaired_by_poll': len(repaired_ids),
            'mean_ms': round(statistics.mean(samples)*1000, 3),
            'p95_ms': round(ordered[max(0, int(len(ordered)*.95)-1)]*1000, 3),
            'max_ms': round(max(samples)*1000, 3), 'authoritative_reads': reads,
            'rejected_or_fenced_snapshots': errors, 'regressions': regressions,
            'removal_fence_checks': removed_fences, 'same_cut_replay_matches': shadow_pass,
            'unproven_cut_comparisons': shadow_pending}


if __name__ == '__main__':
    results = {'kind': 'synthetic discrete-event reducer/cache replay; NOT display measurements',
               'assumptions': '20ms event / 50ms read; deterministic drop/reorder/burst/reconnect/removal',
               'runtime_global_parity': 'INCONCLUSIVE: HA supplies no global inventory cut',
               'poll_10s': replay(10, False), 'poll_2s': replay(2, False),
               'events_with_60s_repair': replay(60, True)}
    assert all(results[k]['regressions'] == 0 for k in ('poll_10s', 'poll_2s', 'events_with_60s_repair'))
    assert results['events_with_60s_repair']['rejected_or_fenced_snapshots'] > 0
    assert results['events_with_60s_repair']['dropped_events_repaired_by_poll'] > 0
    print(json.dumps(results, indent=2))
