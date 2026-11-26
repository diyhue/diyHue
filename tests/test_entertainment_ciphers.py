import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# The guard keeps the shared configManager stub of other test modules intact.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

from services.entertainment import (  # noqa: E402
    DEFAULT_ENTERTAINMENT_CIPHERS,
    entertainment_ciphers,
)


class EntertainmentCipherTests(unittest.TestCase):
    """The cipher list of the DTLS entertainment server is configurable.

    The HDMI Sync Box negotiates PSK-AES128-CBC-SHA and never starts the
    handshake without CBC in the list. Other clients prefer GCM, so the
    default offers both and an installation can replace the list.
    """

    def test_default_offers_cbc_and_gcm(self):
        self.assertIn("PSK-AES128-CBC-SHA", DEFAULT_ENTERTAINMENT_CIPHERS)
        self.assertIn("PSK-AES128-GCM-SHA256", DEFAULT_ENTERTAINMENT_CIPHERS)
        self.assertIn("@SECLEVEL=0", DEFAULT_ENTERTAINMENT_CIPHERS)

    def test_without_configuration_the_default_is_used(self):
        self.assertEqual(entertainment_ciphers({}), DEFAULT_ENTERTAINMENT_CIPHERS)
        self.assertEqual(entertainment_ciphers({"entertainment": {}}),
                         DEFAULT_ENTERTAINMENT_CIPHERS)

    def test_configured_list_is_used(self):
        config = {"entertainment": {"ciphers": "PSK-AES128-GCM-SHA256:@SECLEVEL=0"}}
        self.assertEqual(entertainment_ciphers(config),
                         "PSK-AES128-GCM-SHA256:@SECLEVEL=0")

    def test_configured_list_is_stripped(self):
        config = {"entertainment": {"ciphers": "  PSK-AES128-CCM:@SECLEVEL=0  "}}
        self.assertEqual(entertainment_ciphers(config),
                         "PSK-AES128-CCM:@SECLEVEL=0")

    def test_empty_or_wrong_value_falls_back_to_the_default(self):
        for value in ("", "   ", None, 42, ["PSK-AES128-CCM"]):
            with self.subTest(value=value):
                config = {"entertainment": {"ciphers": value}}
                self.assertEqual(entertainment_ciphers(config),
                                 DEFAULT_ENTERTAINMENT_CIPHERS)


if __name__ == "__main__":
    unittest.main()
