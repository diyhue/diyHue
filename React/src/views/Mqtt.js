import { useState, useEffect } from "react";
import axios from "axios";
import Flash from "../containers/Flash";

const Mqtt = ({ HOST_IP, API_KEY }) => {
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");
  const [enable, setEnable] = useState(false);
  const [mqttServer, setMqttServer] = useState("mqtt");
  const [mqttPort, setMqttPort] = useState(1883);
  const [mqttUser, setMqttUser] = useState("");
  const [mqttPass, setMqttPass] = useState("");
  const [discoveryPrefix, setDiscoveryPrefix] = useState("homeassistant");

  useEffect(() => {
    axios
      .get(`${HOST_IP}/api/${API_KEY}/config/mqtt`)
      .then((result) => {
        setEnable(result.data["enabled"]);
        if ("mqttServer" in result.data)
          setMqttServer(result.data["mqttServer"]);
        if ("mqttPort" in result.data)
          setMqttPort(result.data["mqttPort"]);
        if ("mqttUser" in result.data)
          setMqttUser(result.data["mqttUser"]);
        if ("mqttPassword" in result.data)
          setMqttPass(result.data["mqttPassword"]);
        if ("discoveryPrefix" in result.data)
          setDiscoveryPrefix(result.data["discoveryPrefix"]);
      })
      .catch((error) => {
        console.error(error);
      });
  }, [HOST_IP, API_KEY]);

  const onSubmit = (e) => {
    console.log("submit");
    e.preventDefault();
    axios
      .put(`${HOST_IP}/api/${API_KEY}/config`, {
        mqtt: {
          enabled: enable,
          mqttServer: mqttServer,
          mqttPort: mqttPort,
          mqttUser: mqttUser,
          mqttPassword: mqttPass,
          discoveryPrefix: discoveryPrefix,
        },
      })
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage("Successfully saved, please restart the service");
        setType("success");
      })
      .catch((error) => {
        console.error(error);
        setMessage("Error occured, check browser console");
        setType("error");
      });
  };

  return (
    <div className="inner">
      {type !== "none" && (
        <Flash
          type={type}
          message={message}
          duration="5000"
          setType={setType}
        />
      )}
      <div className="contentContainer">
        <div className="headline">ZigBee2MQTT config</div>
        <form className="add-form" method="POST" onSubmit={(e) => onSubmit(e)}>
          <div className="switchContainer">
            <label className="switch">
              <input
                type="checkbox"
                value={enable}
                checked={enable}
                onChange={(e) => setEnable(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>
          <div className="form-control">
            <label>MQTT server</label>
            <input
              type="text"
              placeholder="MQTT server"
              value={mqttServer}
              onChange={(e) => setMqttServer(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>MQTT port</label>
            <input
              type="number"
              placeholder="MQTT port"
              value={mqttPort}
              onChange={(e) => setMqttPort(parseInt(e.target.value))}
            />
          </div>
          <div className="form-control">
            <label>MQTT username</label>
            <input
              type="text"
              placeholder="MQTT username"
              value={mqttUser}
              onChange={(e) => setMqttUser(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>MQTT password</label>
            <input
              type="text"
              placeholder="MQTT password"
              value={mqttPass}
              onChange={(e) => setMqttPass(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>Discovery Prefix</label>
            <input
              type="text"
              placeholder="Discovery prefix"
              value={discoveryPrefix}
              onChange={(e) => setDiscoveryPrefix(e.target.value)}
            />
          </div>
          <div className="form-control">
            <input type="submit" value="Save" className="btn btn-block" />
          </div>
        </form>
      </div>
    </div>
  );
};

export default Mqtt;
