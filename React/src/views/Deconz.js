import { useState, useEffect } from "react";
import axios from "axios";
import Flash from "../containers/Flash";

const Deconz = ({ HOST_IP, API_KEY }) => {
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");
  const [enable, setEnable] = useState(false);
  const [deconzHost, setDeconzHost] = useState("127.0.0.1");
  const [deconzPort, setDeconzPort] = useState(8443);
  const [deconzUser, setDeconzUser] = useState("");

  useEffect(() => {
    axios
      .get(`${HOST_IP}/api/${API_KEY}/config/deconz`)
      .then((result) => {
        setEnable(result.data["enabled"]);
        if ("deconzHost" in result.data)
          setDeconzHost(result.data["deconzHost"]);
        if ("deconzPort" in result.data)
          setDeconzPort(result.data["deconzPort"]);
        if ("deconzUser" in result.data)
          setDeconzUser(result.data["deconzUser"]);
      })
      .catch((error) => {
        console.error(error);
      });
  }, [HOST_IP, API_KEY]);

  const pairDeconz = (e) => {
    e.preventDefault();
    axios
      .post(
        `http://${deconzHost}:${deconzPort}/api`,
        { devicetype: "diyhue#bridge" },
        { timeout: 2000 }
      )
      .then((result) => {
        if ("success" in result.data[0]) {
          setDeconzUser(result.data[0]["success"]["username"]);
          axios
            .put(`${HOST_IP}/api/${API_KEY}/config`, {
              deconz: {
                enabled: enable,
                deconzHost: deconzHost,
                deconzPort: deconzPort,
                deconzUser: result.data[0]["success"]["username"],
              },
            })
            .then((fetchedData) => {
              console.log(fetchedData.data);
              setMessage("Connected, service restart required.");
              setType("none");
              setType("success");
            });
        } else {
          setMessage(result.data[0]["error"]["description"]);
          setType("none");
          setType("error");
        }
      })
      .catch((error) => {
        console.error(error);
        setMessage(error.message);
        setType("none");
        setType("error");
      });
  };

  const toggleEnable = (e) => {
    setEnable(e);
    axios
      .put(`${HOST_IP}/api/${API_KEY}/config`, { deconz: { enabled: e } })
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage(`Deconz ${e ? "enabled" : "disabled"}`);
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
      <div className="contentContainer">
        <div className="headline">Deconz Config</div>
        <form className="add-form" onSubmit={(e) => pairDeconz(e)}>
          <div className="switchContainer">
            <label className="switch">
              <input
                type="checkbox"
                value={enable}
                checked={enable}
                onChange={(e) => toggleEnable(e.target.checked)}
              />
              <span className="slider"></span>
            </label>
          </div>
          <div className="form-control">
            <label>Deconz host</label>
            <input
              type="text"
              placeholder="Deconz host"
              value={deconzHost}
              onChange={(e) => setDeconzHost(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>Deconz port</label>
            <input
              type="number"
              placeholder="Deconz port"
              value={deconzPort}
              onChange={(e) => setDeconzPort(parseInt(e.target.value))}
            />
          </div>
          <div className="form-control">
            <label>Deconz User</label>
            <input
              type="text"
              placeholder="Automatically populated"
              readOnly
              value={deconzUser}
            />
          </div>
          <div className="form-control">
            <input
              type="submit"
              value={
                typeof deconzUser === "string" && deconzUser.length > 0
                  ? "Pair again"
                  : "Pair"
              }
              className="btn btn-block"
            />
          </div>
        </form>
      </div>
    </div>
  );
};

export default Deconz;
