import logManager

logging = logManager.logger.get_logger(__name__)

class ResourceLink():
    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.classid = data["classid"]
        self.description = data["description"] if "description" in data else ""
        self.links = data["links"] if "links" in data else []
        self.owner = data["owner"]
        self.recycle = data["recycle"] if "recycle" in data else False

    def __del__(self):
        logging.info(self.name + " ResourceLink was destroyed.")

    def add_link(self, link):
        self.links.append("/" + link.getObjectPath()
                          ["resource"] + "/" + link.getObjectPath()["id"])

    def getObjectPath(self):
        return {"resource": "resourcelinks", "id": self.id_v1}

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["description"] = self.description
        result["type"] = "Link"
        result["classid"] = self.classid
        result["owner"] = self.owner.username
        result["recycle"] = self.recycle
        result["links"] = self.links
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
