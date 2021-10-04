import { useState, useEffect } from "react";
import axios from "axios";
import Flash from "../containers/Flash";
import Dropdown from "react-dropdown";
import "react-dropdown/style.css";

const Bridge = ({ HOST_IP, API_KEY }) => {
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");
  const [bridgeName, setBridgeName] = useState("");
  const [swversion, setSwversion] = useState("");
  const [apiVersion, setApiVersion] = useState("");
  const [remoteApi, setRemoteApi] = useState(false);
  const [timezone, setTimezone] = useState("");
  const [timezones, setTimezones] = useState([]);
  const [readonlyConf, setReadonlyConf] = useState({});

  useEffect(() => {
    const fetchTimezones = () => {
      if (API_KEY !== undefined) {
        axios
          .get(`${HOST_IP}/api/${API_KEY}/info/timezones`)
          .then((fetchedData) => {
            console.log(fetchedData.data);
            setTimezones(fetchedData.data);
          })
          .catch((error) => {
            console.error(error);
          });
      }
    };

    fetchTimezones();
    axios
      .get(`${HOST_IP}/api/${API_KEY}/config`)
      .then((result) => {
        setBridgeName(result.data["name"]);
        setSwversion(result.data["swversion"]);
        setApiVersion(result.data["apiversion"]);
        setRemoteApi(result.data["Remote API enabled"]);
        setTimezone(result.data["timezone"]);
        setReadonlyConf(result.data);
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
        name: bridgeName,
        swversion: swversion,
        apiversion: apiVersion,
        timezone: timezone,
        "Remote API enabled": remoteApi,
      })
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage("Successfully saved");
        setType("none");
        setType("success");
      })
      .catch((error) => {
        console.error(error);
        setMessage("Error occured, check browser console");
        setType("none");
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
      <div className="contentContainer spacer">
        <div className="headline">Bridge Config</div>
          <form className="add-form" onSubmit={(e) => onSubmit(e)}>
            <div className="form-control">
              <label>Bridge Name</label>
              <input
                type="text"
                placeholder="Bridge Name"
                value={bridgeName}
                onChange={(e) => setBridgeName(e.target.value)}
              />
            </div>
            <div className="form-control">
              <label>Software Version</label>
              <input
                type="text"
                placeholder="swversion"
                value={swversion}
                onChange={(e) => setSwversion(e.target.value)}
              />
              <p>
                <a href="https://www.philips-hue.com/en-gb/support/release-notes/bridge">
                  check here for last versions
                </a>
              </p>
            </div>
            <div className="form-control">
              <label>API Version</label>
              <input
                type="text"
                placeholder="apiversion"
                value={apiVersion}
                onChange={(e) => setApiVersion(e.target.value)}
              />
            </div>
            <div className="form-control">
              <label>Timezone</label>
              <Dropdown
                options={timezones}
                value={timezone}
                onChange={(e) => setTimezone(e.value)}
                placeholder="Choose light modelid"
              />
            </div>
            <div className="switchContainer">
              <p>Remote API </p>
              <label className="switch">
                <input
                  type="checkbox"
                  value={remoteApi}
                  checked={remoteApi}
                  onChange={(e) => setRemoteApi(e.target.checked)}
                />
                <span className="slider"></span>
              </label>
            </div>
            <div className="form-control">
              <input type="submit" value="Save" className="btn btn-block" />
            </div>
          </form>
      </div>

      <div className="contentContainer">
        <div className="headline">Readonly Config</div>
          <div className="form-control">
            <label>BridgeID</label>
            <input
              readOnly
              type="text"
              placeholder="bridgeid"
              value={readonlyConf["bridgeid"]}
            />
          </div>
          <div className="form-control">
            <label>Ip Address</label>
            <input
              readOnly
              type="text"
              placeholder="ip"
              value={readonlyConf["ipaddress"]}
            />
          </div>
          <div className="form-control">
            <label>Mac</label>
            <input
              readOnly
              type="text"
              placeholder="mac"
              value={readonlyConf["mac"]}
            />
          </div>
          <div className="form-control">
            <label>Local time</label>
            <input
              readOnly
              type="text"
              placeholder="time"
              value={Date(readonlyConf["localtime"])}
            />
          </div>

      </div>
    </div>
    
 
  );
};

export default Bridge;
