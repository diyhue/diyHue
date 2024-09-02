import uuid
import logManager
from HueObjects import genV2Uuid, StreamEvent
from datetime import datetime, timezone

logging = logManager.logger.get_logger(__name__)

class BehaviorInstance():
    def __init__(self, data):
        self.id_v2 = data["id"] if "id" in data else genV2Uuid()
        self.id_v1 = self.id_v2  # used for config save
        self.name = data["metadata"]["name"] if "name" in data["metadata"] else None
        self.configuration = data["configuration"]
        self.enabled = data["enabled"] if "enabled" in data else False
        self.active = data["active"] if "active" in data else False
        self.script_id = data["script_id"] if "script_id" in data else ""

        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Api()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        StreamEvent(streamMessage)

    def __del__(self):
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2, "type": "behavior_instance"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        StreamEvent(streamMessage)
        logging.info(self.name + " behaviour instance was destroyed.")

    def getV2Api(self):
        result = {"configuration": self.configuration,
                  "dependees": [],
                  "enabled": self.enabled,
                  "id": self.id_v2,
                  "last_error": "",
                  "metadata": {
                      "name": "noname"
                  },
                  "script_id": self.script_id,
                  "status": "running" if self.enabled else "disabled",
                  "type": "behavior_instance"
                  }

        if self.name != None:
            result["metadata"]["name"] = self.name

        for resource in self.configuration["where"]:
            result["dependees"].append({"level": "critical",
                                        "target": {
                                            "rid": resource[list(resource.keys())[0]]["rid"],
                                            "rtype": resource[list(resource.keys())[0]]["rtype"]
                                        },
                                        "type": "ResourceDependee"
                                        })

        return result

    def update_attr(self, newdata):
        for key, value in newdata.items():
            if key == "metadata" and "name" in value:
                self.name = value["name"]
                continue
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)
        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Api()],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        StreamEvent(streamMessage)

    def save(self):
        result = {"id": self.id_v2, "metadata": {"name": self.name}, "configuration": self.configuration, "enabled": self.enabled, "active": self.active,
                  "script_id": self.script_id}
        if self.name != None:
            result["metadata"] = {"name": self.name}

        return result
