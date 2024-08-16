import uuid
import logManager
from threading import Thread
from datetime import datetime, timezone
from HueObjects import genV2Uuid, StreamEvent

logging = logManager.logger.get_logger(__name__)

class SmartScene():

    DEFAULT_SPEED = 60000#ms

    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.appdata = data["appdata"] if "appdata" in data else {}
        self.type = data["type"] if "type" in data else "smart_scene"
        self.image = data["image"] if "image" in data else None
        self.action = data["action"] if "action" in data else "deactivate"
        self.lastupdated = data["lastupdated"] if "lastupdated" in data else datetime.now(timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%S")
        self.timeslots = data["timeslots"] if "timeslots" in data else {}
        self.recurrence = data["recurrence"] if "recurrence" in data else {}
        self.speed = data["transition_duration"] if "transition_duration" in data else self.DEFAULT_SPEED
        self.group = data["group"] if "group" in data else None
        self.state = data["state"] if "state" in data else "inactive"
        self.active_timeslot = data["active_timeslot"] if "active_timeslot" in data else 0
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Api()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        streamMessage["data"][0].update(self.getV2Api())
        StreamEvent(streamMessage)

    def __del__(self):
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2, "type": "smart_scene"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        streamMessage["id_v1"] = "/smart_scene/" + self.id_v1
        StreamEvent(streamMessage)
        logging.info(self.name + " smart_scene was destroyed.")

    def activate(self, data):
        # activate smart scene
        if "recall" in data:
            if data["recall"]["action"] == "activate":
                logging.debug("activate smart_scene: " + self.name + " scene: " + str(self.active_timeslot))
                self.state = "active"
                if datetime.now().strftime("%A").lower() in self.recurrence:
                    from flaskUI.v2restapi import getObject
                    target_object = getObject(self.timeslots[self.active_timeslot]["target"]["rtype"], self.timeslots[self.active_timeslot]["target"]["rid"])
                    putDict = {"recall": {"action": "active", "duration": self.speed}}
                    target_object.activate(putDict)
                return
            if data["recall"]["action"] == "deactivate":
                from functions.scripts import findGroup
                group = findGroup(self.group["rid"])
                group.setV1Action(state={"on": False})
                logging.debug("deactivate smart_scene: " + self.name)
                self.state = "inactive"
                return


    def getV2Api(self):
        result = {}
        result["metadata"] = {}
        if self.image != None:
            result["metadata"]["image"] = {"rid": self.image,
                                           "rtype": "public_image"}
        result["metadata"]["name"] = self.name
        result["id"] = self.id_v2
        result["id_v1"] = "/smart_scene/" + self.id_v1
        result["group"] = self.group
        result["type"] = "smart_scene"
        result["week_timeslots"] = [{"timeslots": self.timeslots, "recurrence": self.recurrence}]
        result["transition_duration"] = self.speed
        result["state"] = self.state
        result["active_timeslot"] = {"timeslot_id": self.active_timeslot if self.active_timeslot >= 0 else len(self.timeslots)-1 , "weekday": str(datetime.now().strftime("%A")).lower()}
        return result

    def update_attr(self, newdata):
        self.lastupdated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "appdata": self.appdata, "type": self.type, "image": self.image,
                  "lastupdated": self.lastupdated, "state": self.state, "group": self.group, "active_timeslot": self.active_timeslot }
        if self.timeslots != None:
            result["timeslots"] = self.timeslots
            result["recurrence"] = self.recurrence
        result["speed"] = self.speed or self.DEFAULT_SPEED

        return result
