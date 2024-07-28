import logManager
from datetime import datetime, timezone

logging = logManager.logger.get_logger(__name__)

class Schedule():
    def __init__(self, data):
        self.name = data["name"] if "name" in data else "schedule " + \
            data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.description = data["description"] if "description" in data else "none"
        self.command = data["command"] if "command" in data else {}
        self.localtime = data["localtime"] if "localtime" in data else None
        self.created = data["created"] if "created" in data else datetime.now(timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%S")
        self.status = data["status"] if "status" in data else "disabled"
        self.autodelete = data["autodelete"] if "autodelete" in data else False
        starttime = None
        if data["localtime"].startswith("PT") or data["localtime"].startswith("R"):
            starttime = self.created
        self.starttime = data["starttime"] if "starttime" in data else starttime
        self.recycle = data["recycle"] if "recycle" in data else False

    def __del__(self):
        logging.info(self.name + " schedule was destroyed.")

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["description"] = self.description
        result["command"] = self.command
        if self.localtime != None:
            result["localtime"] = self.localtime
            result["time"] = self.localtime
        result["created"] = self.created
        result["status"] = self.status
        if not self.localtime.startswith("W"):
            result["autodelete"] = self.autodelete
        if self.starttime != None:
            result["starttime"] = self.starttime
        result["recycle"] = self.recycle
        return result

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)
            if key == "status" and value == "enabled":
                logging.debug("enable timer " + self.name)
                self.starttime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    def getObjectPath(self):
        return {"resource": "schedules", "id": self.id_v1}

    def save(self):
        return self.getV1Api()
