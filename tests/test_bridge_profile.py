import importlib.util
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

CONFIG_INIT_SPEC = importlib.util.spec_from_file_location(
    "motionaware_test_config_init",
    BRIDGE_EMULATOR / "configManager" / "configInit.py",
)
configInit = importlib.util.module_from_spec(CONFIG_INIT_SPEC)
CONFIG_INIT_SPEC.loader.exec_module(configInit)


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

    def test_runtime_profile_selection_is_explicit(self):
        config = {"config": {"bridge_profile": "classic"}}
        args = {
            "HOST_IP": "192.168.1.10",
            "FULLMAC": "02:00:00:00:00:01",
            "MAC": "020000000001",
            "BRIDGE_PROFILE": "pro",
        }
        updated = configInit.write_args(args, config)
        self.assertEqual(updated["config"]["bridge_profile"], "pro")

    def test_no_runtime_override_preserves_saved_profile(self):
        config = {"config": {"bridge_profile": "pro"}}
        args = {
            "HOST_IP": "192.168.1.10",
            "FULLMAC": "02:00:00:00:00:01",
            "MAC": "020000000001",
            "BRIDGE_PROFILE": None,
        }
        updated = configInit.write_args(args, config)
        self.assertEqual(updated["config"]["bridge_profile"], "pro")


if __name__ == "__main__":
    unittest.main()
