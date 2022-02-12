import { useState, useEffect } from "react";
import axios from "axios";
import Flash from "../containers/Flash";

const HA = ({ HOST_IP, API_KEY }) => {
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");
  const [enable, setEnable] = useState(false);
  const [homeAssistantIp, setHomeAssistantIp] = useState("127.0.0.1");
  const [homeAssistantPort, setHomeAssistantPort] = useState(8123);
  const [homeAssistantToken, setHomeAssistantToken] = useState("");
  const [homeAssistantIncludeByDefault, setHomeAssistantIncludeByDefault] = useState(true);
  const [homeAssistantUseHttps, setHomeAssistantUseHttps] = useState(false);

  useEffect(() => {
    axios
      .get(`${HOST_IP}/api/${API_KEY}/config/homeassistant`)
      .then((result) => {
        setEnable(result.data["enabled"]);
        if ("homeAssistantIp" in result.data)
          setHomeAssistantIp(result.data["homeAssistantIp"]);
        if ("homeAssistantPort" in result.data)
          setHomeAssistantPort(result.data["homeAssistantPort"]);
        if ("homeAssistantToken" in result.data)
          setHomeAssistantToken(result.data["homeAssistantToken"]);
        if ("homeAssistantIncludeByDefault" in result.data)
          setHomeAssistantIncludeByDefault(result.data["homeAssistantIncludeByDefault"]);
        if ("homeAssistantUseHttps" in result.data)
          setHomeAssistantUseHttps(result.data["homeAssistantUseHttps"]);

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
        homeassistant: {
          enabled: enable,
          homeAssistantIp: homeAssistantIp,
          homeAssistantPort: homeAssistantPort,
          homeAssistantToken: homeAssistantToken,
          homeAssistantIncludeByDefault: homeAssistantIncludeByDefault,
          homeAssistantUseHttps: homeAssistantUseHttps
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
        <div className="headline">Home Assistant config</div>
        <form className="add-form" onSubmit={(e) => onSubmit(e)}>
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
            <label>Home Assistant IP</label>
            <input
              type="text"
              placeholder="IP or hostname"
              value={homeAssistantIp}
              onChange={(e) => setHomeAssistantIp(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>Home Assistant port</label>
            <input
              type="number"
              placeholder="8123"
              value={homeAssistantPort}
              onChange={(e) => setHomeAssistantPort(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>Home Assistant token</label>
            <input
              type="text"
              placeholder="Token"
              value={homeAssistantToken}
              onChange={(e) => setHomeAssistantToken(e.target.value)}
            />
          </div>
          <div className="switchContainer">
            <p>Included by default</p>
            <label className="switch">
              <input
                type="checkbox"
                value={homeAssistantIncludeByDefault}
                checked={homeAssistantIncludeByDefault}
                onChange={(e) => setHomeAssistantIncludeByDefault(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>
          <div className="switchContainer">
            <p>enable HTTPS</p>
            <label className="switch">
              <input
                type="checkbox"
                value={homeAssistantUseHttps}
                checked={homeAssistantUseHttps}
                onChange={(e) => setHomeAssistantUseHttps(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>
          <div className="form-control">
            <input type="submit" value="Save" className="btn btn-block" />
          </div>
        </form>
      </div>
    </div>
  );
};

export default HA;
