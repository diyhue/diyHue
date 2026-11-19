"""Keep mutation responses, readback and stream events on the same V2 IDs."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
import uuid
from unittest.mock import Mock, patch

from flask import Flask
from flask_restful import Api

ROOT = Path(__file__).resolve().parents[1] / 'BridgeEmulator'
sys.path.insert(0, str(ROOT))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.config = {key: {} for key in (
            'device', 'groups', 'lights', 'scenes', 'sensors',
            'geofence_clients', 'smart_scene', 'behavior_instance')}
        self.config['groups']['0'] = types.SimpleNamespace(id_v2=str(uuid.uuid4()), type='LightGroup')
        self.config['config'] = dict(
            bridgeid='001788FFFE123456', name='Test bridge',
            timezone='Europe/London', swversion='1948086000', apiversion='1.65.0')
        self.bridge_config = types.SimpleNamespace(yaml_config=self.config, save_config=Mock())
        self.events = Mock()
        hue = types.ModuleType('HueObjects')
        for name in ('Group', 'EntertainmentConfiguration', 'Scene', 'BehaviorInstance',
                     'GeofenceClient', 'SmartScene', 'Device'):
            setattr(hue, name, types.SimpleNamespace())
        hue.StreamEvent = self.events
        hue.genV2Uuid = lambda: str(uuid.uuid4())
        hue.v1StateToV2 = hue.v2StateToV1 = hue.setGroupAction = Mock()
        modules = {
            'HueObjects': hue,
            'configManager': types.SimpleNamespace(bridgeConfig=self.bridge_config),
            'logManager': types.SimpleNamespace(logger=types.SimpleNamespace(get_logger=lambda _: Mock())),
            'services.entertainment': types.SimpleNamespace(entertainmentService=Mock()),
            'functions.scripts': types.SimpleNamespace(behaviorScripts=Mock()),
            'lights.discover': types.SimpleNamespace(scanForLights=Mock()),
            'functions.daylightSensor': types.SimpleNamespace(daylightSensor=Mock()),
        }
        with patch.dict(sys.modules, modules):
            hue.Group = load('identity_group', 'HueObjects/Group.py')
            # Load MotionAware against the same isolated config, without leaking it.
            modules['functions.motionAware'] = load('identity_motion', 'functions/motionAware.py')
            with patch.dict(sys.modules, modules):
                self.api = load('identity_api', 'flaskUI/v2restapi.py')
        dependencies = patch.dict(sys.modules, modules)
        dependencies.start()
        self.addCleanup(dependencies.stop)
        self.api.authorizeV2 = lambda headers: {'user': object()} if headers.get('hue-application-key') == 'test-key' else {}
        app = Flask(__name__)
        app.testing = True
        rest = Api(app)
        rest.add_resource(self.api.ClipV2Resource, '/clip/v2/resource/<resource>')
        rest.add_resource(self.api.ClipV2ResourceId, '/clip/v2/resource/<resource>/<resourceid>')
        self.client = app.test_client()
        self.headers = {'hue-application-key': 'test-key'}
        self.addCleanup(self.config['groups'].clear)

    def get(self, resource, rid=None, headers=None):
        path = '/clip/v2/resource/' + resource + ('/' + rid if rid else '')
        return self.client.get(path, headers=self.headers if headers is None else headers)

    def test_bridge_rename_readback_and_response(self):
        for profile in ('classic', 'pro'):
            with self.subTest(profile=profile):
                self.config['config']['bridge_profile'] = profile
                device = self.get('device').json['data'][-1]
                rid = device['id']
                response = self.client.put('/clip/v2/resource/device/' + rid,
                    headers=self.headers, json={'metadata': {'name': 'Renamed bridge'}})
                self.assertEqual(response.json, {'errors': [], 'data': [{'rid': rid, 'rtype': 'device'}]})
                readback = self.get('device', rid).json['data'][0]
                self.assertEqual(readback['metadata']['name'], 'Renamed bridge')
                self.assertEqual(self.events.call_args.args[0]['data'][0]['id'], rid)
                self.bridge_config.save_config.assert_called_with(backup=False, resource='config')
                bridge = self.get('bridge').json['data'][0]
                self.assertEqual(self.get('bridge', bridge['id']).json, {'errors': [], 'data': [bridge]})

    def test_created_room_and_zone_ids_match_reads_and_add_event(self):
        for resource in ('room', 'zone'):
            with self.subTest(resource=resource):
                self.events.reset_mock()
                response = self.client.post('/clip/v2/resource/' + resource,
                    headers=self.headers, json={'metadata': {'name': 'Test area', 'archetype': 'other'}, 'children': []})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['errors'], [])
                rid = response.json['data'][0]['rid']
                listed = self.get(resource).json['data'][-1]
                self.assertEqual(rid, listed['id'])
                self.assertEqual(self.get(resource, rid).json, {'errors': [], 'data': [listed]})
                self.assertNotEqual(rid, list(self.config['groups'].values())[-1].id_v2)
                messages = [message for call in self.events.call_args_list
                            for message in (call.args[0] if isinstance(call.args[0], list) else [call.args[0]])]
                added = [item for message in messages if message['type'] == 'add'
                         for item in message['data'] if item['type'] == resource]
                self.assertEqual([item['id'] for item in added], [rid])

    def test_unknown_ids_and_authorization(self):
        for resource in ('bridge', 'device', 'room', 'zone'):
            self.assertEqual(self.get(resource, str(uuid.uuid4())).json, {'errors': [], 'data': []})
            self.assertEqual(self.get(resource, str(uuid.uuid4()), headers={}).status_code, 403)
        self.assertEqual(self.client.post('/clip/v2/resource/room', json={}).status_code, 403)
        self.assertEqual(self.client.put('/clip/v2/resource/device/test', json={}).status_code, 403)


if __name__ == '__main__':
    unittest.main()
