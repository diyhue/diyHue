"""Connection construction must never resolve names in the bridge process."""
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'BridgeEmulator'))
import logManager
logManager.logger.configure_logger('CRITICAL')
from services import homeAssistantWS as ha
from services.haEventClient import EventSession, make_client_class, resolve_address


class ResolutionTests(unittest.TestCase):
    def test_resolution_timeout_kills_and_reaps_child(self):
        child = Mock()
        child.communicate.side_effect = [subprocess.TimeoutExpired('resolver', .01), ('', '')]
        with patch('services.haEventClient.subprocess.Popen', return_value=child):
            with self.assertRaises(TimeoutError):
                resolve_address('example.invalid', 8123, .01)
        child.kill.assert_called_once()
        self.assertEqual(child.communicate.call_count, 2)

    def test_numeric_addresses_need_no_process(self):
        with patch('services.haEventClient.subprocess.Popen') as spawn:
            family, address = resolve_address('::1', 8123, 1)
        self.assertEqual(family, socket.AF_INET6)
        self.assertEqual(address, ('::1', 8123, 0, 0))
        spawn.assert_not_called()

    def test_constructor_uses_only_numeric_library_address_preserving_tls_identity(self):
        owner = SimpleNamespace(read_timeout=15, stop=threading.Event(), reducer=SimpleNamespace(epoch=1))
        real = socket.getaddrinfo
        def numeric_only(host, *args, **kwargs):
            self.assertIn(host, ('127.0.0.1', '::1'))
            return real(host, *args, **kwargs)
        cls = make_client_class(ha.HomeAssistantClient)
        with patch('socket.getaddrinfo', side_effect=numeric_only), \
                patch('services.haEventClient.resolve_address', return_value=(socket.AF_INET, ('192.0.2.1', 8123))):
            client = cls('wss://example.invalid:8123/api/websocket', 'synthetic', '/fake/ca', owner, 1)
            try:
                self.assertEqual(client.host, 'example.invalid')
                self.assertEqual(client.bind_addr, ('192.0.2.1', 8123))
                self.assertIn(b'Host: example.invalid:8123', client.handshake_request)
            finally:
                client.close_connection()

    def test_resolver_rejects_wrong_family_or_non_numeric_result(self):
        for result in [[socket.AF_INET, ['example.invalid', 8123]], [socket.AF_UNIX, ['/fake/socket']]]:
            child = Mock(returncode=0)
            child.communicate.return_value = (json.dumps(result), '')
            with patch('services.haEventClient.subprocess.Popen', return_value=child):
                with self.assertRaises(ValueError):
                    resolve_address('example.invalid', 8123, 1)

    def test_actual_stalled_resolver_is_terminated_and_reaped(self):
        real_spawn = subprocess.Popen
        children = []
        def stalled(args, **kwargs):
            child = real_spawn([sys.executable, '-I', '-c', 'import time; time.sleep(60)'], **kwargs)
            children.append(child)
            return child
        started = time.monotonic()
        with patch('services.haEventClient.subprocess.Popen', side_effect=stalled):
            with self.assertRaises(TimeoutError):
                resolve_address('example.invalid', 8123, .1)
        self.assertLess(time.monotonic() - started, 3)
        self.assertIsNotNone(children[0].returncode)

    def test_ipv6_settings_form_valid_tls_url(self):
        cfg = {'homeAssistantUseHttps': True, 'homeAssistantIp': '::1',
               'homeAssistantPort': 8123, 'homeAssistantToken': 'synthetic'}
        owner = EventSession({'lights': {}, 'config': {'homeassistant': cfg}}, Mock(), Mock())
        self.assertEqual(owner.settings()[0], 'wss://[::1]:8123/api/websocket')

    def test_resolution_and_upgrade_share_one_attempt_deadline(self):
        clock = [0.0]
        owner = SimpleNamespace(read_timeout=15, stop=threading.Event(), reducer=SimpleNamespace(epoch=1))
        def slow_resolve(*args):
            clock[0] = 14.0
            return socket.AF_INET, ('192.0.2.1', 8123)
        transport = Mock()
        transport.connect.side_effect = lambda address: clock.__setitem__(0, 16.0)
        transport.recv.return_value = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n\r\n'
        context = Mock()
        context.wrap_socket.return_value = transport
        with patch('services.haEventClient.time.monotonic', side_effect=lambda: clock[0]), \
                patch('services.haEventClient.resolve_address', side_effect=slow_resolve):
            client = make_client_class(ha.HomeAssistantClient)(
                'wss://example.invalid:8123/api/websocket', 'synthetic', '/fake/ca', owner, 1)
            raw = client.sock
            client.handshake_ok = Mock()
            client.process_response_line = Mock()
            client.process_handshake_header = Mock(return_value=([], []))
            try:
                with patch('services.haEventClient.ssl.create_default_context', return_value=context):
                    with self.assertRaises(TimeoutError):
                        client.connect()
                client.handshake_ok.assert_not_called()
                self.assertLessEqual(transport.settimeout.call_args.args[0], 1)
            finally:
                raw.close()

    def test_failure_backoff_starts_after_slow_attempt_finishes(self):
        import certifi
        clock = [0.0]
        cfg = {'homeAssistantEventReflection': True, 'homeAssistantUseHttps': True,
               'homeAssistantIp': 'example.invalid', 'homeAssistantPort': 8123,
               'homeAssistantToken': 'synthetic', 'homeAssistantCaFile': certifi.where()}
        factory = Mock()
        def slow_failure():
            clock[0] = 14
            raise TimeoutError('synthetic')
        factory.return_value.connect.side_effect = slow_failure
        session = EventSession({'lights': {}, 'config': {'homeassistant': cfg}}, factory, Mock())
        with patch('services.haEventClient.time.monotonic', side_effect=lambda: clock[0]), \
                patch('services.haEventClient.random.uniform', return_value=0):
            session.tick(0)
            self.assertEqual(session.next_connect, 16)
            session.tick(14.25)
            self.assertEqual(factory.call_count, 1)
