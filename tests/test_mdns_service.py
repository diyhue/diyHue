import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1] / "BridgeEmulator"
sys.path.insert(0, str(ROOT))


class FakeServiceInfo:
    def __init__(self, service_type, name, **kwargs):
        self.service_type = service_type
        self.name = name
        self.__dict__.update(kwargs)


class MdnsServiceTests(unittest.TestCase):
    def test_hue_record_has_standard_instance_name_and_pro_properties(self):
        zeroconf = types.ModuleType("zeroconf")
        zeroconf.IPVersion = types.SimpleNamespace(V4Only="v4")
        zeroconf.ServiceInfo = FakeServiceInfo
        zeroconf.Zeroconf = object
        log_manager = types.ModuleType("logManager")
        log_manager.logger = types.SimpleNamespace(get_logger=lambda _name: object())

        with patch.dict(sys.modules, {"zeroconf": zeroconf, "logManager": log_manager}):
            spec = importlib.util.spec_from_file_location(
                "mdns_service_test", ROOT / "services" / "mdns.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        info = module.mdnsServiceInfo(
            "192.0.2.1", 443, "BSB003", "001788FFFE123456"
        )
        self.assertEqual(info.service_type, "_hue._tcp.local.")
        self.assertEqual(info.name, "Philips Hue - 123456._hue._tcp.local.")
        self.assertEqual(info.server, "philips-hue-123456.local.")
        self.assertEqual(info.port, 443)
        self.assertEqual(info.properties, {"modelid": "BSB003", "bridgeid": "001788FFFE123456"})

    def test_classic_record_keeps_its_existing_instance_name(self):
        zeroconf = types.ModuleType("zeroconf")
        zeroconf.IPVersion = types.SimpleNamespace(V4Only="v4")
        zeroconf.ServiceInfo = FakeServiceInfo
        zeroconf.Zeroconf = object
        log_manager = types.ModuleType("logManager")
        log_manager.logger = types.SimpleNamespace(get_logger=lambda _name: object())

        with patch.dict(sys.modules, {"zeroconf": zeroconf, "logManager": log_manager}):
            spec = importlib.util.spec_from_file_location(
                "mdns_classic_service_test", ROOT / "services" / "mdns.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        info = module.mdnsServiceInfo("192.0.2.1", 80, "BSB002", "001788FFFE123456")
        self.assertEqual(info.name, "DIYHue-001788FFFE123456._hue._tcp.local.")
        self.assertEqual(info.server, "DIYHue-001788FFFE123456.local.")


if __name__ == "__main__":
    unittest.main()
