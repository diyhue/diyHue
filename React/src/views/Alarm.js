import { useState, useEffect } from "react";
import axios from "axios";
import Flash from "../containers/Flash";

const Alarm = ({ HOST_IP, API_KEY }) => {
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");
  const [enable, setEnable] = useState(false);
  const [email, setEmail] = useState("none");

  useEffect(() => {
    axios
      .get(`${HOST_IP}/api/${API_KEY}/config/alarm`)
      .then((result) => {
        setEnable(result.data["enabled"]);
        setEmail(result.data["email"]);
      })
      .catch((error) => {
        console.error(error);
      });
  }, [HOST_IP, API_KEY]);

  const toggleEnable = (e) => {
    setEnable(e);
    axios
      .put(`${HOST_IP}/api/${API_KEY}/config`, { alarm: { enabled: e } })
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage(`Alarm ${e ? "activated" : "deactivated"}`);
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

  const onSubmit = (e) => {
    e.preventDefault();
    axios
      .put(`${HOST_IP}/api/${API_KEY}/config`, {
        alarm: { enabled: enable, email: email },
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
      <div className="contentContainer">
      <div className="headline">Motion notifications alarm</div>
        <form className="add-form" onSubmit={(e) => onSubmit(e)}>
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
            <label>e-mail</label>
            <input
              type="text"
              placeholder="Notification email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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

export default Alarm;
