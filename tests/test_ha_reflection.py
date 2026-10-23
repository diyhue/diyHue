"""Deterministic reducer tests; no HA connection or bridge config access."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'BridgeEmulator'))
from services.haReflection import Reflector


def state(value='on', revision=1, **attributes):
    return {'entity_id': 'light.test', 'state': value,
            'last_updated': f'2026-01-01T00:00:{revision:02d}+00:00',
            'attributes': {'diyhue': 'include', **attributes}}


class ReflectionTests(unittest.TestCase):
    def setUp(self):
        self.light = SimpleNamespace(protocol='homeassistant_ws',
            protocol_cfg={'entity_id': 'light.test'}, state={'on': True, 'bri': 100})
        self.r = Reflector({'1': self.light}, lambda s: s is not None and
                           s.get('attributes', {}).get('diyhue') == 'include')
        self.epoch = self.r.new_session()

    def baseline(self, rows=None):
        ticket = self.r.begin_snapshot(self.epoch)
        return self.r.snapshot(self.epoch, ticket, [state()] if rows is None else rows)

    def test_event_reflects_into_served_light(self):
        self.assertTrue(self.baseline())
        self.r.event(self.epoch, 'light.test', state('off', 2))
        self.assertFalse(self.light.state['on'])

    def test_unavailable_retains_values(self):
        self.baseline()
        self.r.event(self.epoch, 'light.test', state('unavailable', 2))
        self.assertTrue(self.light.state['on'])
        self.assertEqual(self.light.state['bri'], 100)
        self.assertFalse(self.light.state['reachable'])

    def test_old_snapshot_cannot_overwrite_event(self):
        self.baseline()
        ticket = self.r.begin_snapshot(self.epoch)
        self.r.event(self.epoch, 'light.test', state('off', 3))
        self.assertFalse(self.r.snapshot(self.epoch, ticket, [state('on', 2)]))
        self.assertFalse(self.light.state['on'])

    def test_tombstone_requires_authoritative_recreation(self):
        self.baseline()
        self.r.event(self.epoch, 'light.test', None)
        self.assertFalse(self.r.command_allowed(self.light))
        self.r.event(self.epoch, 'light.test', state('on', 2))
        self.assertFalse(self.r.command_allowed(self.light))
        self.assertTrue(self.baseline([state('off', 3)]))
        self.assertTrue(self.r.command_allowed(self.light))
        self.assertFalse(self.light.state['on'])

    def test_partial_snapshot_never_deletes(self):
        self.baseline()
        ticket = self.r.begin_snapshot(self.epoch)
        self.assertFalse(self.r.snapshot(self.epoch, ticket, [{'entity_id': 'broken'}]))
        self.assertTrue(self.r.command_allowed(self.light))

    def test_old_epoch_is_fenced(self):
        self.baseline()
        self.r.new_session()
        self.r.event(self.epoch, 'light.test', state('off', 5))
        self.assertTrue(self.light.state['on'])
        self.assertFalse(self.r.command_allowed(self.light))

    def test_equal_timestamp_conflict_requests_reconcile(self):
        self.baseline()
        self.r.event(self.epoch, 'light.test', state('off', 1))
        self.assertTrue(self.r.needs_sync)
        self.assertTrue(self.light.state['on'])

    def test_snapshot_deletion_event_overlap_is_ambiguous(self):
        self.baseline()
        ticket = self.r.begin_snapshot(self.epoch)
        self.r.event(self.epoch, 'light.test', None)
        self.assertFalse(self.r.snapshot(self.epoch, ticket, [state('on', 2)]))
        self.assertFalse(self.r.command_allowed(self.light))

    def test_absence_cannot_be_undone_by_delayed_event(self):
        self.baseline([])
        self.r.event(self.epoch, 'light.test', state())
        self.assertFalse(self.r.command_allowed(self.light))


if __name__ == '__main__':
    unittest.main()


class AdditionalReducerTests(unittest.TestCase):
    setUp = ReflectionTests.setUp
    baseline = ReflectionTests.baseline

    def test_old_same_epoch_snapshot_token_is_fenced(self):
        old = self.r.begin_snapshot(self.epoch)
        new = self.r.begin_snapshot(self.epoch)
        self.assertTrue(self.r.snapshot(self.epoch, new, [state('off', 4)]))
        self.assertFalse(self.r.snapshot(self.epoch, old, [state('on', 5)]))
        self.assertFalse(self.light.state['on'])

    def test_coalescing_does_not_erase_deletion_barrier(self):
        self.baseline()
        ticket = self.r.begin_snapshot(self.epoch)
        self.r.event(self.epoch, 'light.test', None)
        self.r.event(self.epoch, 'light.test', state('off', 3))
        self.assertFalse(self.r.snapshot(self.epoch, ticket, [state('on', 4)]))
        self.assertFalse(self.r.command_allowed(self.light))

    def test_unmapped_noise_is_not_retained(self):
        self.baseline()
        for i in range(5000):
            row = state()
            row['entity_id'] = f'light.unmapped_{i}'
            self.r.event(self.epoch, row['entity_id'], row)
        self.assertEqual(set(self.r.rows), {'light.test'})
        self.assertFalse(self.r.pending)
        self.assertFalse(self.r.tombstones)

    def test_bad_translation_cannot_partially_delete(self):
        self.baseline()
        bad = state('on', 3, color_mode='hs', hs_color=[])
        # Empty hs_color means absent; a non-numeric nonempty value is malformed.
        bad['attributes']['hs_color'] = ['bad', 'bad']
        ticket = self.r.begin_snapshot(self.epoch)
        self.assertFalse(self.r.snapshot(self.epoch, ticket, [bad]))
        self.assertEqual(self.r.rows['light.test'], state())

    def test_detached_or_replaced_light_cannot_dispatch(self):
        self.baseline()
        original = self.light
        self.r.lights['1'] = SimpleNamespace(protocol='homeassistant_ws',
            protocol_cfg={'entity_id': 'light.test'}, state={'on': True})
        self.assertFalse(self.r.command_allowed(original))
        self.assertFalse(self.r.command_allowed(self.r.lights['1']))
        self.baseline()
        self.assertTrue(self.r.command_allowed(self.r.lights['1']))

    def test_retired_tombstones_are_pruned(self):
        self.baseline()
        self.r.event(self.epoch, 'light.test', None)
        self.r.lights.clear()
        self.r.begin_snapshot(self.epoch)
        self.assertFalse(self.r.tombstones)
        self.assertFalse(self.r.rows)

class ReviewRegressionTests(unittest.TestCase):
    setUp = ReflectionTests.setUp
    baseline = ReflectionTests.baseline

    def test_report_only_metadata_does_not_block_poll_or_reconnect_baseline(self):
        first = state()
        first['last_reported'] = '2026-01-01T00:00:01+00:00'
        self.assertTrue(self.baseline([first]))
        second = dict(first, last_reported='2026-01-01T00:00:02+00:00')
        self.assertTrue(self.baseline([second]))
        self.epoch = self.r.new_session()
        third = dict(first, last_reported='2026-01-01T00:00:03+00:00')
        self.assertTrue(self.baseline([third]))
        self.assertTrue(self.r.command_allowed(self.light))

    def test_report_only_event_during_snapshot_is_compatible(self):
        self.baseline()
        ticket = self.r.begin_snapshot(self.epoch)
        self.r.event(self.epoch, 'light.test', dict(state(), last_reported='2026-01-01T00:00:04+00:00'))
        self.assertTrue(self.r.snapshot(self.epoch, ticket, [state()]))
        conflict = state('off')
        self.r.event(self.epoch, 'light.test', conflict)
        self.assertTrue(self.r.needs_sync)
        self.assertTrue(self.light.state['on'])

    def test_mapping_overflow_disables_event_publication_and_command_authority(self):
        self.r.max_pending = 1
        self.baseline()
        extra = SimpleNamespace(protocol='homeassistant_ws', protocol_cfg={'entity_id': 'light.extra'}, state={'on': False})
        self.r.lights['2'] = extra
        self.assertFalse(self.r.command_allowed(self.light))
        for n in range(2, 7):
            candidate = state('on', n)
            candidate['entity_id'] = 'light.extra'
            self.r.begin_snapshot(self.epoch)
            self.assertFalse(self.r.snapshot(self.epoch, self.r.snapshot_token, [state(), candidate]))
            self.r.event(self.epoch, 'light.extra', candidate)
            self.assertFalse(self.r.ready)
            self.assertLessEqual(len(self.r.rows), self.r.max_pending)
            self.assertFalse(extra.state['on'])
        self.epoch = self.r.new_session()
        self.assertFalse(self.r.command_allowed(self.light))
        del self.r.lights['2']
        self.assertTrue(self.baseline())
        self.assertTrue(self.r.command_allowed(self.light))
