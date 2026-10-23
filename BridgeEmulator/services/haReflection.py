"""Conservative, serialized HA cache reflection for existing Hue mappings only.

HA has no global snapshot revision. Overlapping snapshot/event cuts that cannot
be proved using entity timestamps are rejected, never ordered by local arrival.
"""
from copy import deepcopy
from datetime import datetime
from threading import RLock


def revision(row):
    stamp = datetime.fromisoformat(row['last_updated'].replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('HA timestamp must have timezone')
    return stamp


def state_content(row):
    # last_reported and context can change without a state/attribute revision.
    return row['entity_id'], row['state'], row['attributes']


def translate(existing, row):
    result = deepcopy(existing)
    available = row['state'] in ('on', 'off')
    result['reachable'] = available
    if not available:
        return result
    result['on'] = row['state'] == 'on'
    attrs = row['attributes']
    if result['on']:
        for source, target in [('brightness', 'bri'), ('color_temp', 'ct'), ('xy_color', 'xy')]:
            if source in attrs and attrs[source] is not None:
                result[target] = deepcopy(attrs[source])
        mode = attrs.get('color_mode')
        if mode == 'color_temp':
            if attrs.get('color_temp_kelvin'):
                result['ct'] = round(1000000 / attrs['color_temp_kelvin'])
            result['colormode'] = 'ct'
        elif mode in ('xy', 'rgb', 'rgbw', 'rgbww') and attrs.get('xy_color'):
            result['colormode'] = 'xy'
        elif mode == 'hs' and attrs.get('hs_color'):
            result['hue'] = round(attrs['hs_color'][0] * 65535 / 360)
            result['sat'] = round(attrs['hs_color'][1] * 254 / 100)
            result['colormode'] = 'hs'
    return result


class Reflector:
    def __init__(self, lights, included, max_pending=4096):
        self.lights = lights
        self.included = included
        self.max_pending = max_pending
        self.lock = RLock()
        self.epoch = 0
        self.rows = {}
        self.qualified_mappings = set()
        self.tombstones = set()
        self.pending = {}
        self.sequence = 0
        self.snapshot_token = 0
        self.ambiguous = False
        self.ready = False
        self.needs_sync = True

    def new_session(self):
        with self.lock:
            self.epoch += 1
            self.ready = False
            self.needs_sync = True
            self.pending.clear()
            self.snapshot_token += 1
            self.ambiguous = False
            return self.epoch

    def disconnect(self, epoch):
        with self.lock:
            if epoch == self.epoch:
                self.ready = False
                self.needs_sync = True
                for light in list(self.lights.values()):
                    if light.protocol == 'homeassistant_ws':
                        light.state['reachable'] = False

    def begin_snapshot(self, epoch):
        with self.lock:
            if epoch != self.epoch:
                return None
            self.mapping_budget()
            mapped = self.mapped_entities()
            self.rows = {entity: row for entity, row in self.rows.items() if entity in mapped}
            self.tombstones.intersection_update(mapped)
            self.pending.clear()
            self.ambiguous = False
            self.snapshot_token += 1
            return self.snapshot_token

    def mapped_entities(self):
        return {light.protocol_cfg.get('entity_id') for light in list(self.lights.values())
                if light.protocol == 'homeassistant_ws'}

    def mapping_budget(self):
        if len(self.mapped_entities()) > self.max_pending:
            self.ready = False
            self.needs_sync = True
            return False
        return True

    def _valid(self, row):
        if not isinstance(row, dict):
            return False
        try:
            revision(row)
            return (isinstance(row['entity_id'], str) and isinstance(row['state'], str)
                    and isinstance(row['attributes'], dict))
        except (KeyError, ValueError, TypeError, AttributeError):
            return False

    def _publish(self, entity, row):
        if row is None or not self.included(row):
            self.rows.pop(entity, None)
            self.tombstones.add(entity)
        else:
            self.rows[entity] = deepcopy(row)
            self.tombstones.discard(entity)
        for light in list(self.lights.values()):
            if light.protocol == 'homeassistant_ws' and light.protocol_cfg.get('entity_id') == entity:
                if entity in self.tombstones:
                    light.state['reachable'] = False
                else:
                    light.state.update(translate(light.state, row))

    def event(self, epoch, entity, row):
        with self.lock:
            if epoch != self.epoch:
                return
            if row is not None and (not self._valid(row) or row['entity_id'] != entity):
                self.needs_sync = True
                return
            if not self.mapping_budget():
                return
            if entity not in self.mapped_entities():
                return
            self.sequence += 1
            if len(self.pending) >= self.max_pending and entity not in self.pending:
                self.ready = False
                self.needs_sync = True
                return
            # Keep one candidate per entity. Conflicting or regressed timestamps
            # are ambiguous; a full reconcile must establish the next safe cut.
            previous = self.pending.get(entity)
            if entity in self.pending and (previous is None or row is None or not self.included(previous) or not self.included(row)):
                self.ambiguous = True
            if previous is not None and row is not None:
                if revision(row) < revision(previous) or (revision(row) == revision(previous) and state_content(row) != state_content(previous)):
                    self.needs_sync = True
                    self.ready = False
                    return
            self.pending[entity] = deepcopy(row)
            if not self.ready:
                return
            current = self.rows.get(entity)
            if row is not None and entity in self.tombstones:
                self.needs_sync = True
                return
            if row is not None and current is not None:
                if revision(row) < revision(current):
                    return
                if revision(row) == revision(current) and state_content(row) != state_content(current):
                    self.needs_sync = True
                    return
            try:
                for light in list(self.lights.values()):
                    if light.protocol == 'homeassistant_ws' and light.protocol_cfg.get('entity_id') == entity and row is not None and self.included(row):
                        translate(light.state, row)
            except (TypeError, ValueError, IndexError, KeyError, ZeroDivisionError, OverflowError):
                self.needs_sync = True
                return
            self._publish(entity, row)

    def snapshot(self, epoch, ticket, rows):
        with self.lock:
            if epoch != self.epoch or ticket != self.snapshot_token or ticket is None:
                return False
            if not isinstance(rows, list) or any(not self._valid(row) for row in rows):
                self.needs_sync = True
                return False
            all_entities = [row['entity_id'] for row in rows]
            mapped = self.mapped_entities()
            candidate = {row['entity_id']: row for row in rows if row['entity_id'] in mapped}
            if not self.mapping_budget() or self.ambiguous or len(set(all_entities)) != len(rows):
                self.needs_sync = True
                return False
            for entity, event in self.pending.items():
                snapshot = candidate.get(entity)
                # HA get_states has no deletion timestamp or global cut token.
                if event is None or snapshot is None or not self.included(event):
                    self.needs_sync = True
                    return False
                if revision(snapshot) < revision(event) or (revision(snapshot) == revision(event) and state_content(snapshot) != state_content(event)):
                    self.needs_sync = True
                    return False
            for entity, current in self.rows.items():
                snapshot = candidate.get(entity)
                if snapshot is not None and (revision(snapshot) < revision(current) or
                        (revision(snapshot) == revision(current) and state_content(snapshot) != state_content(current))):
                    self.needs_sync = True
                    return False
            # Prepare every translation before mutating any served light. Malformed
            # values make the whole baseline invalid, never a partial deletion.
            try:
                for light in list(self.lights.values()):
                    if light.protocol == 'homeassistant_ws':
                        row = candidate.get(light.protocol_cfg.get('entity_id'))
                        if row is not None and self.included(row):
                            translate(light.state, row)
            except (TypeError, ValueError, IndexError, KeyError, ZeroDivisionError, OverflowError):
                self.needs_sync = True
                return False
            entities = set(candidate) | set(self.rows) | self.tombstones
            entities.update(light.protocol_cfg.get('entity_id') for light in list(self.lights.values())
                            if light.protocol == 'homeassistant_ws')
            for entity in entities:
                self._publish(entity, candidate.get(entity))
            self.pending.clear()
            self.qualified_mappings = {(id(light), light.protocol_cfg.get('entity_id'))
                                       for light in list(self.lights.values()) if light.protocol == 'homeassistant_ws'}
            self.ready = True
            self.needs_sync = False
            return True

    def command_allowed(self, light):
        with self.lock:
            if not self.mapping_budget():
                return False
            entity = light.protocol_cfg.get('entity_id')
            member = any(candidate is light for candidate in list(self.lights.values()))
            return (member and (id(light), entity) in self.qualified_mappings and self.ready
                    and entity in self.rows and entity not in self.tombstones and self.included(self.rows[entity])
                    and self.rows[entity]['state'] in ('on', 'off'))
