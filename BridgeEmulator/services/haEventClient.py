"""Opt-in HA session supervisor; legacy websocket path remains the default."""
import random
import certifi
import ssl
import threading
import time
from services.haReflection import Reflector
from ws4py.exc import HandshakeError


class EventSession:
    """One worker, one outstanding read, bounded retries, baseline on each epoch."""
    poll_seconds = 60
    read_timeout = 15
    retry_seconds = 2

    def __init__(self, bridge, client_class, include):
        self.bridge = bridge
        self.client_class = client_class
        self.reducer = Reflector(bridge['lights'], include)
        self.stop = threading.Event()
        self.lifecycle_lock = threading.RLock()
        self.client = None
        self.fingerprint = None
        self.next_connect = 0
        self.failures = 0

    def start(self):
        threading.Thread(target=self.run, name='ha-reflection', daemon=True).start()

    def settings(self):
        cfg = self.bridge['config']['homeassistant']
        if not cfg.get('homeAssistantUseHttps'):
            raise ValueError('HA event reflection requires verified TLS')
        ca = cfg.get('homeAssistantCaFile') or ssl.get_default_verify_paths().cafile or certifi.where()
        if not ca:
            raise ValueError('HA event reflection requires a trusted CA file')
        url = 'wss://{}:{}/api/websocket'.format(cfg['homeAssistantIp'], cfg['homeAssistantPort'])
        return url, cfg['homeAssistantToken'], ca

    def retire(self):
        with self.lifecycle_lock:
            self.stop.set()
            self.invalidate()

    def invalidate(self):
        with self.lifecycle_lock:
            self._invalidate()

    def _invalidate(self):
        client, self.client = self.client, None
        self.reducer.new_session()
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
            finally:
                try:
                    client.close_connection()
                except Exception:
                    pass

    def tick(self, now):
        with self.lifecycle_lock:
            disabled = self._tick(now)
        if disabled == 'disable':
            # Never acquire the global ownership lock under lifecycle_lock.
            from services import homeAssistantWS
            homeAssistantWS.disable_event_session(self)

    def _tick(self, now):
        if self.stop.is_set():
            return
        if not self.bridge['config']['homeassistant'].get('homeAssistantEventReflection', False):
            self.invalidate()
            self.stop.set()
            return 'disable'
        settings = self.settings()
        if self.fingerprint != settings:
            ssl.create_default_context(cafile=settings[2])
            self.invalidate()
            self.fingerprint = settings
            self.next_connect = now
        client = self.client
        if client is not None and (client.client_terminated or now >= client.deadline):
            self.invalidate()
            self.failures = min(self.failures + 1, 5)
            self.next_connect = now + min(60, 2 ** self.failures) + random.uniform(0, 1)
            client = None
        if client is None:
            if now < self.next_connect:
                return
            epoch = self.reducer.new_session()
            client = self.client_class(*settings, owner=self, epoch=epoch)
            self.client = client
            try:
                client.connect()
            except Exception:
                self.invalidate()
                self.failures = min(self.failures + 1, 5)
                self.next_connect = now + min(60, 2 ** self.failures) + random.uniform(0, 1)
            return
        with self.reducer.lock:
            if client.subscribed and now >= client.next_ping:
                if len(client.id_to_type) >= 256:
                    client.deadline = 0
                    return
                client._send_with_id({'type': 'ping'}, 'ping')
                client.next_ping = now + 5
            if client.subscribed and client.inflight is None and now >= client.next_read:
                client.get_all_lights()

    def run(self):
        while not self.stop.wait(0.25):
            try:
                self.tick(time.monotonic())
            except Exception:
                # No endpoint, token, raw HA payload or exception text in logs.
                self.invalidate()
                self.next_connect = time.monotonic() + 60
                self.stop.wait(2)


def make_client_class(legacy):
    class EventClient(legacy):
        def __init__(self, url, token, ca, owner, epoch):
            self.owner, self.epoch, self.token = owner, epoch, token
            self.message_id = 1
            self.id_to_type = {}
            self.subscribed = False
            self.inflight = None
            self.read_failures = 0
            self.next_read = 0
            self.next_ping = 0
            self.deadline = time.monotonic() + owner.read_timeout
            super().__init__(url, ssl_options={'cert_reqs': ssl.CERT_REQUIRED, 'ca_certs': ca})
            self.sock.settimeout(owner.read_timeout)

        def connect(self):
            # ws4py's stock HTTP upgrade has neither a total deadline nor a
            # header-size bound. Keep its parser/thread startup, bound the I/O.
            deadline = time.monotonic() + self.owner.read_timeout
            def bounded():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('HA connection deadline')
                self.sock.settimeout(remaining)
            try:
                if self.scheme != 'wss':
                    raise ValueError('HA reflection requires TLS')
                context = ssl.create_default_context(cafile=self.ssl_options['ca_certs'])
                bounded()
                self.sock = context.wrap_socket(self.sock, server_hostname=self.host,
                                                do_handshake_on_connect=False)
                self._is_secure = True
                bounded()
                self.sock.connect(self.bind_addr)
                bounded()
                self.sock.do_handshake()
                bounded()
                self._write(self.handshake_request)
                response = b''
                while b'\r\n\r\n' not in response:
                    bounded()
                    chunk = self.sock.recv(128)
                    if not chunk:
                        raise HandshakeError('Incomplete HA websocket upgrade')
                    response += chunk
                    if len(response) > 16384:
                        raise HandshakeError('HA websocket upgrade header too large')
                bounded()
                headers, _, body = response.partition(b'\r\n\r\n')
                response_line, _, headers = headers.partition(b'\r\n')
                self.process_response_line(response_line)
                self.protocols, self.extensions = self.process_handshake_header(headers)
                self.sock.settimeout(self.owner.read_timeout)
                self.deadline = time.monotonic() + self.owner.read_timeout
                self.handshake_ok()
                if body:
                    self.process(body)
            except Exception:
                self.close_connection()
                raise

        def opened(self):
            # ws4py.run calls setblocking(True) immediately before this hook.
            self.sock.settimeout(self.owner.read_timeout)

        def current(self):
            return (not self.owner.stop.is_set() and self.epoch == self.owner.reducer.epoch)

        def do_auth_required(self, message):
            if self.current():
                self._send({'type': 'auth', 'access_token': self.token})

        def do_auth_complete(self):
            if self.current():
                self.subscribe_for_updates()

        def do_auth_invalid(self, message):
            self.deadline = 0

        def get_all_lights(self):
            with self.owner.reducer.lock:
                if not self.current() or not self.subscribed or self.inflight is not None:
                    return
                if len(self.id_to_type) >= 256:
                    self.deadline = 0
                    return
                self.inflight = self.owner.reducer.begin_snapshot(self.epoch)
                self.deadline = time.monotonic() + self.owner.read_timeout
                self._send_with_id({'type': 'get_states'}, 'getstates')

        def do_result(self, message):
            with self.owner.reducer.lock:
                if not self.current():
                    return
                kind = self.id_to_type.pop(message.get('id'), None)
                if kind == 'subscribe':
                    if message.get('success') is True:
                        self.subscribed = True
                        self.get_all_lights()
                    else:
                        self.deadline = 0
                elif kind == 'getstates':
                    ok = message.get('success') is True and self.owner.reducer.snapshot(
                        self.epoch, self.inflight, message.get('result'))
                    self.inflight = None
                    self.deadline = float('inf')
                    self.next_read = time.monotonic() + (self.owner.poll_seconds if ok else self.owner.retry_seconds)
                    if ok:
                        self.read_failures = 0
                        self.owner.failures = 0
                    else:
                        self.read_failures += 1
                        if self.read_failures >= 3:
                            self.deadline = 0
                # call_service replies are popped as well, bounding the id map.

        def do_state_changed(self, message):
            if not self.current():
                return
            try:
                data = message['event']['data']
                entity = data['entity_id']
                if not isinstance(entity, str):
                    raise ValueError('invalid entity')
                if entity.startswith(('light.', 'switch.')):
                    self.owner.reducer.event(self.epoch, entity, data['new_state'])
                    if self.owner.reducer.needs_sync:
                        self.next_read = min(self.next_read, time.monotonic() + self.owner.retry_seconds)
            except (KeyError, TypeError, ValueError):
                self.owner.reducer.needs_sync = True
                self.next_read = min(self.next_read, time.monotonic() + self.owner.retry_seconds)

        def do_pong(self, message):
            if self.current():
                self.id_to_type.pop(message.get('id'), None)

        def closed(self, code, reason=None):
            if self.current():
                self.owner.reducer.disconnect(self.epoch)
            self.deadline = 0

        def change_light(self, light, data):
            with self.owner.reducer.lock:
                if not self.current() or not self.owner.reducer.command_allowed(light):
                    raise ValueError('HA mapping is not authoritative')
                if len(self.id_to_type) >= 256:
                    raise ValueError('HA command response budget exhausted')
                super().change_light(light, data)

    return EventClient
