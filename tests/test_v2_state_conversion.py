from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from HueObjects import v2StateToV1  # noqa: E402


class V2StateToV1Tests(unittest.TestCase):
    def test_dynamics_duration_becomes_transitiontime(self):
        # v2 durations are in milliseconds, v1 transitiontime in 100 ms steps.
        state = v2StateToV1({"on": {"on": True}, "dimming": {"brightness": 50}, "dynamics": {"duration": 4000}})
        self.assertEqual(state, {"on": True, "bri": 127, "transitiontime": 40})

    def test_short_durations_are_rounded(self):
        self.assertEqual(v2StateToV1({"dynamics": {"duration": 0}})["transitiontime"], 0)
        self.assertEqual(v2StateToV1({"dynamics": {"duration": 250}})["transitiontime"], 2)
        self.assertEqual(v2StateToV1({"dynamics": {"duration": 400}})["transitiontime"], 4)

    def test_dynamics_speed_alone_sets_no_transition(self):
        self.assertNotIn("transitiontime", v2StateToV1({"dynamics": {"speed": 0.5}}))


if __name__ == "__main__":
    unittest.main()
