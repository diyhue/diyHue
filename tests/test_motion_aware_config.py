import copy
import pathlib
import sys
import unittest


BRIDGE_EMULATOR = pathlib.Path(__file__).parents[1] / "BridgeEmulator"
sys.path.insert(0, str(BRIDGE_EMULATOR))

from motionAwareConfig import (  # noqa: E402
    get_motion_aware_areas,
    normalize_motion_aware_config,
    read_bool,
    read_int,
    read_health,
    read_participants,
    read_resource_reference,
)


class MotionAwareConfigTests(unittest.TestCase):
    def test_missing_config_does_not_enable_or_mutate_feature(self):
        config = {"bridge_profile": "classic"}
        before = copy.deepcopy(config)
        self.assertEqual(normalize_motion_aware_config(config), (False, []))
        self.assertEqual(config, before)
        self.assertEqual(get_motion_aware_areas(config), {})

    def test_malformed_containers_become_inert_and_idempotent(self):
        for malformed in (None, False, 0, "enabled", []):
            with self.subTest(malformed=malformed):
                config = {"motion_aware": malformed}
                changed, issues = normalize_motion_aware_config(config)
                self.assertTrue(changed)
                self.assertTrue(issues)
                self.assertEqual(config["motion_aware"], {"areas": {}})
                self.assertEqual(
                    normalize_motion_aware_config(config),
                    (False, []),
                )

    def test_missing_areas_is_added_without_losing_unknown_fields(self):
        config = {"motion_aware": {"future_field": {"x": 1}}}
        self.assertEqual(normalize_motion_aware_config(config), (True, []))
        self.assertEqual(config["motion_aware"]["areas"], {})
        self.assertEqual(config["motion_aware"]["future_field"], {"x": 1})

    def test_legacy_container_is_migrated_to_canonical_key(self):
        config = {"motionAware": {"areas": {"old": {}}}}
        changed, issues = normalize_motion_aware_config(config)
        self.assertTrue(changed)
        self.assertEqual(issues, [])
        self.assertNotIn("motionAware", config)
        areas = get_motion_aware_areas(config, create=True)
        areas["new"] = {"enabled": False}
        self.assertEqual(
            config["motion_aware"],
            {"areas": {"old": {}, "new": {"enabled": False}}},
        )

    def test_boolean_reader_preserves_false_and_rejects_ints(self):
        self.assertFalse(read_bool({"enabled": False}, "enabled", True))
        self.assertTrue(read_bool({}, "enabled", True))
        self.assertTrue(read_bool({"enabled": None}, "enabled", True))
        self.assertTrue(read_bool({"enabled": 0}, "enabled", True))

    def test_integer_reader_preserves_zero_and_rejects_bool(self):
        self.assertEqual(read_int({"value": 0}, "value", 2, 0, 4), 0)
        self.assertEqual(read_int({"value": False}, "value", 2, 0, 4), 2)
        self.assertEqual(read_int({"value": 5}, "value", 2, 0, 4), 2)
        self.assertEqual(read_int({"value": None}, "value", 2, 0, 4), 2)

    def test_resource_reference_validation(self):
        self.assertEqual(
            read_resource_reference(
                {"rid": "abc", "rtype": "room"}, ("room",)
            ),
            {"rid": "abc", "rtype": "room"},
        )
        for malformed in (
            None,
            {},
            {"rid": "", "rtype": "room"},
            {"rid": "abc", "rtype": "device"},
        ):
            self.assertIsNone(read_resource_reference(malformed, ("room",)))

    def test_participant_validation_is_canonical_and_non_mutating(self):
        source = [{
            "resource": {"rid": "candidate-1", "rtype": "motion_area_candidate"},
            "status": {"health": "unhealthy"},
            "unknown": "ignored in API mapping",
        }]
        before = copy.deepcopy(source)
        self.assertEqual(
            read_participants(source),
            [{
                "resource": {
                    "rid": "candidate-1",
                    "rtype": "motion_area_candidate",
                },
                    "status": {"health": "unhealthy"},
            }],
        )
        self.assertEqual(source, before)

    def test_health_accepts_only_hue_enum(self):
        self.assertEqual(read_health({"health": "healthy"}), "healthy")
        self.assertEqual(read_health({"health": "unhealthy"}), "unhealthy")
        self.assertEqual(read_health({"health": "degraded"}), "healthy")
        self.assertEqual(read_health({"health": None}), "healthy")

    def test_participant_validation_rejects_duplicates_and_malformed(self):
        participant = {
            "resource": {"rid": "same", "rtype": "motion_area_candidate"}
        }
        self.assertIsNone(read_participants([participant, participant]))
        self.assertIsNone(read_participants([{"resource": None}]))
        self.assertIsNone(read_participants(None))


if __name__ == "__main__":
    unittest.main()
