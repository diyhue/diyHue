import uuid
import logManager
from sensors.sensor_types import sensorTypes
from HueObjects import genV2Uuid, StreamEvent
from datetime import datetime, timezone
from copy import deepcopy

logging = logManager.logger.get_logger(__name__)

class Sensor():
    def __init__(self, data):
        if data["modelid"] in sensorTypes:
            if "manufacturername" not in data:
                data["manufacturername"] = sensorTypes[data["modelid"]
                                                       ][data["type"]]["static"]["manufacturername"]
            if "config" not in data:
                data["config"] = deepcopy(
                    sensorTypes[data["modelid"]][data["type"]]["config"])
            if "state" not in data:
                data["state"] = deepcopy(
                    sensorTypes[data["modelid"]][data["type"]]["state"])
            if "swversion" not in data:
                data["swversion"] = sensorTypes[data["modelid"]
                                                ][data["type"]]["static"]["swversion"]
        if "config" not in data:
            data["config"] = {}
        if "reachable" not in data["config"]:
            data["config"]["reachable"] = True
        if "on" not in data["config"]:
            data["config"]["on"] = True
        if "state" not in data:
            data["state"] = {}
        if "lastupdated" not in data["state"]:
            data["state"]["lastupdated"] = "none"
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.config = data["config"]
        self.modelid = data["modelid"]
        self.manufacturername = data["manufacturername"] if "manufacturername" in data else "Philips"
        self.protocol = data["protocol"] if "protocol" in data else "none"
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {
        }
        self.type = data["type"]
        self.state = data["state"]
        dxstate = {}
        for state in data["state"].keys():
            dxstate[state] = datetime.now()
        self.dxState = dxstate
        self.swversion = data["swversion"] if "swversion" in data else None
        self.recycle = data["recycle"] if "recycle" in data else False
        self.uniqueid = data["uniqueid"] if "uniqueid" in data else None


    def __del__(self):
        logging.info(self.name + " sensor was destroyed.")

    def setV1State(self, state):
        self.state.update(state)

    def getV1Api(self):
        result = {}
        if self.modelid in sensorTypes:
            result = sensorTypes[self.modelid][self.type]["static"]
        result["state"] = self.state
        if self.config != None:
            result["config"] = self.config
        result["name"] = self.name
        result["type"] = self.type
        result["modelid"] = self.modelid
        result["manufacturername"] = self.manufacturername
        if self.swversion != None:
            result["swversion"] = self.swversion
        if self.uniqueid != None:
            result["uniqueid"] = self.uniqueid
        if self.recycle == True:
            result["recycle"] = self.recycle
        return result

    def getObjectPath(self):
        return {"resource": "sensors", "id": self.id_v1}


    def update_attr(self, newdata):
        if self.id_v1 == "1" and "config" in newdata:  # manage daylight sensor
            if "long" in newdata["config"] and "lat" in newdata["config"]:
                self.config["configured"]=True
                self.protocol_cfg={"long": float(
                    newdata["config"]["long"][:-1]), "lat": float(newdata["config"]["lat"][:-1])}
                return
        for key, value in newdata.items():
            updateAttribute=getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def save(self):
        result={}
        result["name"]=self.name
        result["id_v1"]=self.id_v1
        result["id_v2"]=self.id_v2
        result["state"]=self.state
        result["config"]=self.config
        result["type"]=self.type
        result["modelid"]=self.modelid
        result["manufacturername"]=self.manufacturername
        result["uniqueid"]=self.uniqueid
        result["swversion"]=self.swversion
        result["protocol"]=self.protocol
        result["protocol_cfg"]=self.protocol_cfg
        return result
