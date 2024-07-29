import logManager
from datetime import datetime, timezone

logging = logManager.logger.get_logger(__name__)

class Rule():
    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.actions = data["actions"] if "actions" in data else []
        self.conditions = data["conditions"] if "conditions" in data else []
        self.owner = data["owner"]
        self.status = data["status"] if "status" in data else "enabled"
        self.recycle = data["recycle"] if "recycle" in data else False
        self.created = data["created"] if "created" in data else datetime.now(timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%S")
        self.lasttriggered = data["lasttriggered"] if "lasttriggered" in data else "none"
        self.timestriggered = data["timestriggered"] if "timestriggered" in data else 0

    def __del__(self):
        logging.info(self.name + " rule was destroyed.")

    def add_actions(self, action):
        self.actions.append(action)

    def add_conditions(self, condition):
        self.condition.append(condition)

    def getObjectPath(self):
        return {"resource": "rules", "id": self.id_v1}

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["owner"] = self.owner.username
        result["created"] = self.created
        result["lasttriggered"] = self.lasttriggered
        result["timestriggered"] = self.timestriggered
        result["status"] = self.status
        result["recycle"] = self.recycle
        result["conditions"] = self.conditions
        result["actions"] = self.actions
        return result

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def save(self):
        return self.getV1Api()
