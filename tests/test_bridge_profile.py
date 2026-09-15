import pathlib
import sys
import unittest


BRIDGE_EMULATOR = pathlib.Path(__file__).parents[1] / "BridgeEmulator"
sys.path.insert(0, str(BRIDGE_EMULATOR))

from functions.core import (  # noqa: E402
    bridgeIdentity,
    bridgeReportedApiversion,
    bridgeReportedSwversion,
    staticConfig,
)


class BridgeProfileTests(unittest.TestCase):
    def test_default_profile_remains_classic(self):
        identity = bridgeIdentity({})
        self.assertEqual(identity["profile"], "classic")
        self.assertEqual(identity["modelid"], "BSB002")
        self.assertIsNone(identity["apiversion"])
        self.assertEqual(staticConfig({})["modelid"], "BSB002")

    def test_pro_profile_is_explicit_and_data_driven(self):
        config = {"bridge_profile": "pro", "apiversion": "1.75.0", "swversion": "1975104000"}
        identity = bridgeIdentity(config)
        self.assertEqual(identity["profile"], "pro")
        self.assertEqual(identity["modelid"], "BSB003")
        self.assertEqual(bridgeReportedApiversion(config), "1.78.0")
        self.assertEqual(bridgeReportedSwversion(config), "2071442000")
        self.assertEqual(staticConfig(config)["modelid"], "BSB003")


if __name__ == "__main__":
    unittest.main()
