"""Offline regression checks for benchmark statistics and evidence boundaries."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    'ha_benchmark', Path(__file__).resolve().parents[1] / 'examples/benchmark_ha_reflection.py')
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class BenchmarkTests(unittest.TestCase):
    def test_nearest_rank_small_samples(self):
        self.assertEqual(benchmark.nearest_rank_p95(list(range(1, 12))), 11)
        self.assertEqual(benchmark.nearest_rank_p95(list(range(46))), 43)
        self.assertEqual(benchmark.nearest_rank_p95([7]), 7)
        self.assertIsNone(benchmark.nearest_rank_p95([]))

    def test_replay_tail_uses_matching_sample_rank(self):
        slow = benchmark.replay(10, False)
        self.assertEqual(slow['matched'], 11)
        self.assertEqual(slow['p95_ms'], slow['max_ms'])
        self.assertEqual(slow['p95_ms'], 9486.304)
        self.assertEqual(benchmark.replay(2, False)['p95_ms'], 1954.331)

    def test_fixture_requests_are_not_production_efficiency(self):
        result = benchmark.replay(60, True)
        self.assertIn('fixture_stimulus_requests', result)
        self.assertNotIn('authoritative_reads', result)
        self.assertIn('not production', result['scheduling_disclaimer'])
        self.assertIn('row_revision_decreases', result)
        self.assertNotIn('regressions', result)

    def test_shadow_only_seeds_on_reconnect_and_requires_consumed_cut(self):
        audit = []
        result = benchmark.replay(60, True, audit=audit)
        seeds = [entry for entry in audit if entry['kind'] == 'shadow_seed']
        self.assertEqual(len(seeds), 1)
        self.assertEqual(seeds[0]['epoch'], 2)
        comparisons = [entry for entry in audit if entry['kind'] == 'comparison']
        for entry in comparisons:
            if entry['equal']:
                self.assertTrue(entry['ready'])
                self.assertEqual(entry['cut'], entry['consumed_cut'])
        self.assertEqual(result['initial_cut_equalities'], 1)
        self.assertEqual(result['post_change_cut_equalities'],
                         sum(e['equal'] and e['cut'] != 0 for e in comparisons))
        self.assertTrue(any(not e['ready'] and not e['equal'] for e in comparisons))
        recovering = next(e for e in comparisons if e['cut'] == 33)
        self.assertEqual(recovering['consumed_cut'], 33)
        self.assertFalse(recovering['ready'])
        self.assertFalse(recovering['equal'])
        self.assertTrue(any(e['ready'] and e['cut'] != e['consumed_cut']
                            and not e['equal'] for e in comparisons))

    def test_lifecycle_has_separate_coverage_and_no_early_recreation(self):
        for events in (False, True):
            audit = []
            result = benchmark.replay(2, events, audit=audit)
            self.assertEqual(result['brightness_changes'], 67)
            self.assertEqual(result['matched'] + result['missed_or_coalesced'], 67)
            lifecycle = result['lifecycle']
            self.assertEqual(lifecycle['expected'], 2)
            self.assertEqual(lifecycle['matched'] + lifecycle['missed'], 2)
            self.assertEqual(lifecycle['observations']['remove']['latency_ms'],
                             0 if events else 50)
            self.assertGreaterEqual(lifecycle['observations']['restore']['observed_at'], 83)
            self.assertFalse(any(e['kind'] == 'source' and 80 <= e['at'] < 83
                                 for e in audit))
            self.assertTrue(all(not e['reachable'] for e in audit
                                if e['kind'] == 'disconnect'))

    def test_old_epoch_callback_cannot_mutate_reconnected_cache(self):
        audit = []
        result = benchmark.replay(60, True, audit=audit)
        stale = [e for e in audit if e['kind'] == 'stale_callback']
        self.assertGreaterEqual(len(stale), 1)
        self.assertTrue(all(e['unchanged'] and e['callback_epoch'] != e['epoch']
                            for e in stale))
        self.assertEqual(result['stale_epoch_callbacks_fenced'], len(stale))
        self.assertEqual(result['row_revision_decreases'], 0)


if __name__ == '__main__':
    unittest.main()
