import { useState, useEffect } from "react";
import axios from "axios";
import Flash from "../containers/Flash";

const HueBridge = ({ HOST_IP, API_KEY }) => {
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");
  const [bridgeIp, setBridgeIp] = useState("192.168.x.x");
  const [hueUser, setHueUser] = useState("");

  useEffect(() => {
    axios
      .get(`${HOST_IP}/api/${API_KEY}/config/hue`)
      .then((result) => {
        setBridgeIp(result.data["ip"]);
        setHueUser(result.data["hueUser"]);
      })
      .catch((error) => {
        console.error(error);
      });
  }, [HOST_IP, API_KEY]);

  const pairBridge = (e) => {
    e.preventDefault();
    axios
      .post(`http://${bridgeIp}/api`, { devicetype: "diyhue#bridge" })
      .then((result) => {
        if ("success" in result.data[0]) {
          setHueUser(result.data[0]["success"]["username"]);
          axios
            .put(`${HOST_IP}/api/${API_KEY}/config`, {
              hue: {
                ip: bridgeIp,
                hueUser: result.data[0]["success"]["username"],
              },
            })
            .then((fetchedData) => {
              console.log(fetchedData.data);
              setMessage("Connected, now scan for lights");
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
      <div className="headline">Pair original Hue Bridge</div>
        <form className="add-form" onSubmit={(e) => pairBridge(e)}>
          <div className="form-control">
            <label>Bridge Ip</label>
            <input
              type="text"
              placeholder="192.168.x.x"
              value={bridgeIp}
              onChange={(e) => setBridgeIp(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>Hue User</label>
            <input
              type="text"
              placeholder="Automatically populated"
              readOnly
              value={hueUser}
            />
          </div>
          <div className="form-control">
            <input
              type="submit"
              value={
                typeof hueUser === "string" && hueUser.length > 0
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

export default HueBridge;
