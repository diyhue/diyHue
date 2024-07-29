import uuid
import logManager
from datetime import datetime, timezone
from HueObjects import genV2Uuid, StreamEvent

logging = logManager.logger.get_logger(__name__)

class GeofenceClient():
    def __init__(self, data):
        self.name = data.get('name', f'Geofence {data.get("id_v1")}')
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.is_at_home = data.get('is_at_home', False)

        streamMessage = {
            "creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2GeofenceClient()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        StreamEvent(streamMessage)

    def __del__(self):
        streamMessage = {
            "creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "geofence_client"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        StreamEvent(streamMessage)
        logging.info(self.name + " geofence client was destroyed.")

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2GeofenceClient()],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        StreamEvent(streamMessage)

    def getV2GeofenceClient(self):
        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'geofence_client')),
            "name": self.name,
            "type": "geofence_client"
        }
