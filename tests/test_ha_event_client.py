"""Offline adapter tests using actual callbacks and verified SSLContext setup."""
import importlib
import ssl
import certifi
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'BridgeEmulator'))
import logManager
logManager.logger.configure_logger('CRITICAL')
from services import homeAssistantWS as ha
from services.haEventClient import EventSession, make_client_class
from services.haReflection import Reflector


def row(value='on', n=1):
    return {'entity_id': 'light.test', 'state': value, 'attributes': {'diyhue': 'include'},
            'last_updated': f'2026-01-01T00:00:{n:02d}+00:00'}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        resolver = patch('services.haEventClient.resolve_address', return_value=(2, ('192.0.2.1', 8123)))
        resolver.start()
        self.addCleanup(resolver.stop)
        self.light = SimpleNamespace(protocol='homeassistant_ws', protocol_cfg={'entity_id': 'light.test'},
                                     state={'on': True, 'bri': 100})
        self.reducer = Reflector({'1': self.light}, lambda r: r is not None and r['attributes'].get('diyhue') == 'include')
        self.owner = SimpleNamespace(reducer=self.reducer, read_timeout=15, poll_seconds=60,
                                     retry_seconds=2, failures=0, stop=threading.Event())
        self.epoch = self.reducer.new_session()
        cls = make_client_class(ha.HomeAssistantClient)
        # Patch socket construction, preserving every real callback method.
        with patch('ws4py.client.threadedclient.WebSocketClient.__init__', return_value=None):
            with patch.object(cls, 'sock', create=True, new=Mock()):
                self.client = cls('wss://example.invalid:8123/api/websocket', 'test-token',
                                  '/synthetic/ca.pem', owner=self.owner, epoch=self.epoch)
        self.client._send = Mock()

    def test_subscribe_ack_precedes_baseline_and_null_result_is_valid_ack(self):
        self.client.do_auth_complete()
        self.assertEqual(self.client._send.call_args.args[0]['type'], 'subscribe_events')
        self.assertIsNone(self.client.inflight)
        self.client.do_result({'id': 1, 'success': True, 'result': None})
        self.assertEqual(self.client._send.call_args.args[0]['type'], 'get_states')
        self.assertIsNotNone(self.client.inflight)
        self.client.do_result({'id': 2, 'success': True, 'result': [row()]})
        self.assertTrue(self.reducer.ready)
        self.assertFalse(self.client.id_to_type)

    def test_empty_authoritative_baseline_removes_mapping(self):
        self.test_subscribe_ack_precedes_baseline_and_null_result_is_valid_ack()
        self.client.get_all_lights()
        self.client.do_result({'id': 3, 'success': True, 'result': []})
        self.assertFalse(self.reducer.command_allowed(self.light))
        self.assertFalse(self.light.state['reachable'])

    def test_old_close_and_event_cannot_mutate_replacement(self):
        self.test_subscribe_ack_precedes_baseline_and_null_result_is_valid_ack()
        epoch = self.reducer.new_session()
        ticket = self.reducer.begin_snapshot(epoch)
        self.reducer.snapshot(epoch, ticket, [row('on', 3)])
        self.client.closed(1000)
        self.client.do_state_changed({'event': {'data': {'entity_id': 'light.test', 'new_state': row('off', 4)}}})
        self.assertTrue(self.light.state['on'])
        self.assertTrue(self.light.state['reachable'])
        self.assertTrue(self.reducer.ready)

    def test_poll_is_single_flight_and_three_rejections_reconnect(self):
        self.client.subscribed = True
        for index in range(3):
            self.client.get_all_lights()
            before = self.client._send.call_count
            self.client.get_all_lights()
            self.assertEqual(before, self.client._send.call_count)
            self.client.do_result({'id': index + 1, 'success': False})
        self.assertEqual(self.client.deadline, 0)

    def test_protocol_commands_to_tombstone_are_blocked(self):
        self.test_subscribe_ack_precedes_baseline_and_null_result_is_valid_ack()
        self.reducer.event(self.epoch, 'light.test', None)
        with self.assertRaises(ValueError):
            self.client.change_light(self.light, {'on': False})
        self.assertTrue(self.light.state['on'])

    def test_tls_options_activate_required_validation(self):
        cls = make_client_class(ha.HomeAssistantClient)
        with patch('ws4py.client.threadedclient.WebSocketClient.__init__', return_value=None) as init:
            with patch.object(cls, 'sock', create=True, new=Mock()):
                cls('wss://example.invalid/api/websocket', 'test-token', '/trust/ca.pem', self.owner, self.epoch)
        self.assertEqual(init.call_args.kwargs['ssl_options'],
                         {'cert_reqs': ssl.CERT_REQUIRED, 'ca_certs': '/trust/ca.pem'})

    def test_actual_ws4py_context_requires_chain_and_hostname_validation(self):
        # Exercise ws4py's actual context construction without opening a socket.
        from ws4py.client import WebSocketBaseClient
        contexts = []
        real_context = ssl.SSLContext
        def context(protocol):
            ctx = real_context(protocol)
            contexts.append(ctx)
            return ctx
        fake = SimpleNamespace(scheme='wss', ssl_options={'cert_reqs': ssl.CERT_REQUIRED,
            'ca_certs': certifi.where()}, sock=Mock(), host='example.invalid')
        with patch('ws4py.client.ssl.SSLContext', side_effect=context):
            # A non-socket mock deliberately ends execution at wrap_socket.
            with self.assertRaises((TypeError, AttributeError, ValueError, NotImplementedError)):
                WebSocketBaseClient.connect(fake)
        self.assertEqual(contexts[0].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(contexts[0].check_hostname)
        self.assertGreater(contexts[0].cert_store_stats()['x509_ca'], 0)

    def test_plaintext_opt_in_configuration_is_rejected(self):
        bridge = {'lights': {}, 'config': {'homeassistant': {'homeAssistantUseHttps': False}}}
        supervisor = EventSession(bridge, Mock(), Mock())
        with self.assertRaises(ValueError):
            supervisor.settings()

    def test_light_guard_runs_before_optimistic_mutation(self):
        # Import real Light; other regression modules may already provide config stubs.
        sys.modules.setdefault('configManager', SimpleNamespace(bridgeConfig=SimpleNamespace(yaml_config={})))
        from HueObjects.Light import Light
        self.reducer.snapshot(self.epoch, self.reducer.begin_snapshot(self.epoch), [])
        with patch.object(ha, 'event_session', self.owner):
            with self.assertRaises(ValueError):
                Light.setV1State(self.light, {'on': False, 'bri': 3})
        self.assertTrue(self.light.state['on'])
        self.assertEqual(self.light.state['bri'], 100)

    def test_credential_change_fences_old_callbacks_and_requires_baseline(self):
        cfg = {'homeAssistantEventReflection': True, 'homeAssistantUseHttps': True,
               'homeAssistantIp': 'example.invalid', 'homeAssistantPort': 8123,
               'homeAssistantToken': 'first', 'homeAssistantCaFile': certifi.where()}
        bridge = {'lights': {'1': self.light}, 'config': {'homeassistant': cfg}}
        factory = Mock()
        client = factory.return_value
        client.client_terminated = False
        client.deadline = float('inf')
        client.subscribed = False
        supervisor = EventSession(bridge, factory, lambda row: True)
        supervisor.tick(0)
        epoch = supervisor.reducer.epoch
        supervisor.reducer.snapshot(epoch, supervisor.reducer.begin_snapshot(epoch), [row()])
        cfg['homeAssistantToken'] = 'replacement'
        supervisor.tick(1)
        self.assertGreater(supervisor.reducer.epoch, epoch)
        self.assertFalse(supervisor.reducer.ready)
        self.assertEqual(factory.call_args.args[1], 'replacement')
        supervisor.reducer.event(epoch, 'light.test', row('off', 3))
        self.assertTrue(self.light.state['on'])

    def test_timeout_fences_session_and_schedules_bounded_reconnect(self):
        cfg = {'homeAssistantEventReflection': True, 'homeAssistantUseHttps': True,
               'homeAssistantIp': 'example.invalid', 'homeAssistantPort': 8123,
               'homeAssistantToken': 'synthetic', 'homeAssistantCaFile': certifi.where()}
        factory = Mock()
        client = factory.return_value
        client.client_terminated = False
        client.deadline = 15
        supervisor = EventSession({'lights': {}, 'config': {'homeassistant': cfg}}, factory, lambda r: True)
        supervisor.tick(0)
        epoch = supervisor.reducer.epoch
        with patch('services.haEventClient.time.monotonic', return_value=16):
            supervisor.tick(16)
        self.assertIsNone(supervisor.client)
        self.assertGreater(supervisor.reducer.epoch, epoch)
        self.assertLessEqual(supervisor.next_connect, 77)
        supervisor.tick(16.1)
        self.assertEqual(factory.call_count, 1)

    def test_disable_fences_and_restores_legacy_owner(self):
        supervisor = EventSession({'lights': {}, 'config': {'homeassistant': {
            'homeAssistantEventReflection': False}}}, Mock(), Mock())
        epoch = supervisor.reducer.epoch
        with patch.object(ha, 'event_session', supervisor), patch.object(ha, 'create_ws_client') as create:
            supervisor.tick(0)
            self.assertIsNone(ha.event_session)
            create.assert_called_once_with(supervisor.bridge)
        self.assertTrue(supervisor.stop.is_set())
        self.assertGreater(supervisor.reducer.epoch, epoch)

    def test_v1_rest_returns_defined_hue_error_without_mutation(self):
        sys.modules.setdefault('configManager', SimpleNamespace(bridgeConfig=SimpleNamespace(yaml_config={})))
        from flask import Flask
        from flaskUI import restful
        from HueObjects.Light import Light
        light = SimpleNamespace(**vars(self.light))
        light.setV1State = lambda state: Light.setV1State(light, state)
        config = {'lights': {'1': light}, 'apiUsers': {}}
        app = Flask(__name__)
        self.reducer.snapshot(self.epoch, self.reducer.begin_snapshot(self.epoch), [])
        with patch.object(ha, 'event_session', self.owner), patch.object(restful, 'bridgeConfig', config):
            with app.test_request_context('/api/test/lights/1/state', method='PUT', json={'on': False},
                                          environ_base={'REMOTE_ADDR': '127.0.0.1'}):
                result = restful.ElementParam().put('test', 'lights', '1', 'state')
        self.assertEqual(result[0]['error']['type'], 901)
        self.assertTrue(light.state['on'])

    def test_stopped_supervisor_callbacks_cannot_write_during_reconfigure(self):
        self.test_subscribe_ack_precedes_baseline_and_null_result_is_valid_ack()
        self.owner.stop.set()
        self.client.closed(1000)
        self.client.do_state_changed({'event': {'data': {'entity_id': 'light.test', 'new_state': row('off', 3)}}})
        self.assertTrue(self.light.state['on'])
        self.assertTrue(self.light.state['reachable'])

    def test_retirement_serializes_with_tick_paused_after_stop_check(self):
        cfg = {'homeAssistantEventReflection': True}
        supervisor = EventSession({'lights': {}, 'config': {'homeassistant': cfg}}, Mock(), Mock())
        entered, release, retired = threading.Event(), threading.Event(), threading.Event()
        def paused_settings():
            entered.set()
            self.assertTrue(release.wait(2))
            return 'wss://example.invalid', 'synthetic', certifi.where()
        supervisor.settings = paused_settings
        thread = threading.Thread(target=lambda: supervisor.tick(0))
        thread.start()
        self.assertTrue(entered.wait(1))
        def retire():
            supervisor.retire()
            retired.set()
        retire_thread = threading.Thread(target=retire)
        retire_thread.start()
        # The lifecycle lock excludes replacement until the in-flight tick drains.
        self.assertFalse(retired.wait(.02))
        release.set()
        thread.join(2)
        retire_thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertFalse(retire_thread.is_alive())
        self.assertTrue(supervisor.stop.is_set())
        self.assertIsNone(supervisor.client)
        calls = supervisor.client_class.call_count
        supervisor.tick(1)
        self.assertEqual(supervisor.client_class.call_count, calls)

    def test_concurrent_reconfigure_publishes_only_one_active_owner(self):
        cfg = {'homeAssistantEventReflection': True}
        bridge = {'lights': {}, 'config': {'homeassistant': cfg}}
        first, second = Mock(), Mock()
        entered, release = threading.Event(), threading.Event()
        def pause_first():
            entered.set()
            self.assertTrue(release.wait(2))
        first.start.side_effect = pause_first
        errors = []
        def configure():
            try:
                ha.create_ws_client(bridge)
            except Exception as error:
                errors.append(error)
        with patch.object(ha, 'event_session', None), patch('services.haEventClient.EventSession', side_effect=[first, second]):
            a = threading.Thread(target=configure)
            b = threading.Thread(target=configure)
            a.start()
            self.assertTrue(entered.wait(1))
            b.start()
            self.assertFalse(second.start.called)
            release.set()
            a.join(2)
            b.join(2)
            self.assertFalse(a.is_alive() or b.is_alive())
            self.assertFalse(errors)
            first.retire.assert_called_once()
            second.retire.assert_not_called()
            self.assertIs(ha.event_session, second)

    def test_legacy_poll_already_inflight_cannot_overwrite_new_owner(self):
        sys.modules.setdefault('configManager', SimpleNamespace(bridgeConfig=SimpleNamespace(yaml_config={})))
        from services import stateFetch
        self.light.name = 'Synthetic HA light'
        sentinel = RuntimeError('stop synthetic loop')
        def delayed_candidate(light):
            ha.event_session = self.owner
            return {'on': False, 'bri': 1}
        protocol = SimpleNamespace(__name__='lights.protocols.homeassistant_ws',
                                   get_light_state=delayed_candidate)
        config = {'lights': {'1': self.light}, 'apiUsers': {}}
        with patch.object(ha, 'event_session', None), patch.object(stateFetch, 'bridgeConfig', config), \
                patch.object(stateFetch, 'protocols', [protocol]), patch.object(stateFetch, 'sleep', side_effect=sentinel):
            with self.assertRaisesRegex(RuntimeError, 'stop synthetic loop'):
                stateFetch.syncWithLights(False)
        self.assertTrue(self.light.state['on'])
        self.assertEqual(self.light.state['bri'], 100)

    def test_unavailable_commands_cannot_optimistically_restore_reachability(self):
        from HueObjects.Light import Light
        for index, value in enumerate(('unavailable', 'unknown')):
            with self.subTest(value=value):
                epoch = self.reducer.new_session()
                self.reducer.snapshot(epoch, self.reducer.begin_snapshot(epoch), [row(value, 3 + index * 2)])
                self.assertFalse(self.reducer.command_allowed(self.light))
                with patch.object(ha, 'event_session', self.owner):
                    with self.assertRaises(ha.MappingUnavailable):
                        Light.setV1State(self.light, {'on': False, 'bri': 1})
                self.assertFalse(self.light.state['reachable'])
                self.assertTrue(self.light.state['on'])
                self.assertEqual(self.light.state['bri'], 100)
                self.reducer.event(epoch, 'light.test', row('on', 4 + index * 2))
                self.assertTrue(self.reducer.command_allowed(self.light))
                self.assertTrue(self.light.state['reachable'])

    def test_actual_ws4py_run_restores_timeout_after_setblocking(self):
        from ws4py.websocket import WebSocket
        import socket
        left, right = socket.socketpair()
        try:
            self.client.sock = left
            self.client.stream = Mock()
            self.client.heartbeat_freq = None
            self.client.client_terminated = self.client.server_terminated = False
            def once():
                self.assertEqual(left.gettimeout(), self.owner.read_timeout)
                return False
            self.client.once = once
            self.client.terminate = Mock()
            WebSocket.run(self.client)
            self.assertEqual(left.gettimeout(), self.owner.read_timeout)
        finally:
            left.close()
            right.close()

    def handshake_fixture(self):
        self.client.scheme = 'wss'
        self.client.host = 'example.invalid'
        self.client.unix_socket_path = None
        self.client.port = 8123
        self.client.ssl_options = {'ca_certs': certifi.where()}
        request_patch = patch.object(type(self.client), 'handshake_request', b'GET /api/websocket HTTP/1.1\r\n\r\n')
        request_patch.start()
        self.addCleanup(request_patch.stop)
        self.client.sock = Mock()
        self.client._write = Mock()
        self.client.close_connection = Mock()
        self.client.handshake_ok = Mock()
        self.client.process_response_line = Mock()
        self.client.process_handshake_header = Mock(return_value=([], []))
        self.client.process = Mock()
        return self.client.sock

    def test_total_upgrade_deadline_stops_slow_drip(self):
        transport = self.handshake_fixture()
        self.client.deadline = 15
        transport.recv.return_value = b'x'
        context = Mock()
        context.wrap_socket.return_value = transport
        with patch('services.haEventClient.ssl.create_default_context', return_value=context), \
                patch('services.haEventClient.time.monotonic', side_effect=range(100)):
            with self.assertRaises(TimeoutError):
                self.client.connect()
        self.assertLess(transport.recv.call_count, self.owner.read_timeout)
        self.client.close_connection.assert_called_once()
        self.client.handshake_ok.assert_not_called()

    def test_upgrade_header_limit_stops_unbounded_response(self):
        transport = self.handshake_fixture()
        transport.recv.return_value = b'x' * 128
        context = Mock()
        context.wrap_socket.return_value = transport
        with patch('services.haEventClient.ssl.create_default_context', return_value=context), \
                patch('services.haEventClient.time.monotonic', return_value=0):
            with self.assertRaisesRegex(Exception, 'header too large'):
                self.client.connect()
        self.assertEqual(transport.recv.call_count, 129)
        self.client.close_connection.assert_called_once()

    def test_bounded_upgrade_preserves_library_parser_and_starts_reader(self):
        transport = self.handshake_fixture()
        transport.recv.side_effect = [b'HTTP/1.1 101 Switching Protocols\r\n', b'Upgrade: websocket\r\n\r\nbody']
        context = Mock()
        context.wrap_socket.return_value = transport
        with patch('services.haEventClient.ssl.create_default_context', return_value=context):
            self.client.connect()
        context.wrap_socket.assert_called_once_with(transport, server_hostname='example.invalid',
                                                    do_handshake_on_connect=False)
        self.client.process_response_line.assert_called_once_with(b'HTTP/1.1 101 Switching Protocols')
        self.client.handshake_ok.assert_called_once()
        self.client.process.assert_called_once_with(b'body')
        self.assertEqual(transport.settimeout.call_args.args[0], self.owner.read_timeout)

    def test_legacy_event_legacy_toggle_closes_each_prior_transport(self):
        legacy = Mock()
        event_owner = Mock()
        cfg = {'homeAssistantEventReflection': True, 'homeAssistantUseHttps': True, 'homeAssistantIp': 'example.invalid',
               'homeAssistantPort': 8123, 'homeAssistantToken': 'synthetic'}
        bridge = {'lights': {}, 'config': {'homeassistant': cfg}}
        with patch.object(ha, 'event_session', None), patch.object(ha, 'homeassistant_ws_client', legacy), \
                patch('services.haEventClient.EventSession', return_value=event_owner), \
                patch.object(ha, 'connect_if_required') as legacy_connect:
            ha.create_ws_client(bridge)
            legacy.close_connection.assert_called_once()
            legacy.close.assert_called_once()
            self.assertIsNone(ha.homeassistant_ws_client)
            self.assertIs(ha.event_session, event_owner)
            cfg['homeAssistantEventReflection'] = False
            ha.create_ws_client(bridge)
            event_owner.retire.assert_called_once()
            self.assertIsNone(ha.event_session)
            legacy_connect.assert_called_once()

    def test_close_frame_failure_always_hard_closes_fenced_session(self):
        supervisor = EventSession({'lights': {}, 'config': {}}, Mock(), Mock())
        old = Mock()
        old.close.side_effect = TimeoutError('synthetic blocked close')
        supervisor.client = old
        epoch = supervisor.reducer.epoch
        supervisor.invalidate()
        old.close_connection.assert_called_once()
        self.assertIsNone(supervisor.client)
        self.assertGreater(supervisor.reducer.epoch, epoch)
        # Even a broken transport cleanup must not kill the recovery worker.
        old.close_connection.side_effect = OSError('synthetic closed descriptor')
        supervisor.client = old
        supervisor.invalidate()
        self.assertIsNone(supervisor.client)
