from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from services import entertainment  # noqa: E402


class AcceptAddressTests(unittest.TestCase):
    """The DTLS server on port 2100 has to honour --bind-ip (#851)."""

    def accept_address(self, bind_ip):
        config_manager = SimpleNamespace(runtimeConfig=SimpleNamespace(arg={"BIND_IP": bind_ip}))
        with patch.object(entertainment, "configManager", config_manager):
            return entertainment._accept_address()

    def test_bind_ip_limits_the_listener(self):
        self.assertEqual(self.accept_address("192.168.1.20"), "192.168.1.20:2100")

    def test_default_bind_listens_everywhere(self):
        self.assertEqual(self.accept_address("0.0.0.0"), "2100")
        self.assertEqual(self.accept_address(""), "2100")

    def test_missing_runtime_config_listens_everywhere(self):
        with patch.object(entertainment, "configManager", SimpleNamespace()):
            self.assertEqual(entertainment._accept_address(), "2100")


if __name__ == "__main__":
    unittest.main()
