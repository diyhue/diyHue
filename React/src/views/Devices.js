import { useState, useEffect } from "react";
import axios from "axios";
import Device from "../containers/Device";
import Flash from "../containers/Flash";

const Devices = ({ HOST_IP, API_KEY }) => {
  const [devices, setDevices] = useState({});
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");

  const fetchDevices = () => {
    if (API_KEY !== undefined) {
      axios
        .get(`${HOST_IP}/sensors`)
        .then((fetchedData) => {
          console.log(fetchedData.data);
          setDevices(fetchedData.data);
        })
        .catch((error) => {
          console.error(error);
        });
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(() => {
      fetchDevices();
    }, 2000); // <<-- ⏱ 1000ms = 1s
    return () => clearInterval(interval);
  }, [API_KEY]);

  return (
    <div className="content">
      {type !== "none" && (
        <Flash
          type={type}
          message={message}
          duration="5000"
          setType={setType}
        />
      )}
      <div className="cardGrid">
        {Object.entries(devices).map(([id, device]) => (
          <Device
            key={id}
            api_key={API_KEY}
            id={id}
            device={device}
            setType={setType}
            setMessage={setMessage}
          />
        ))}
      </div>
    </div>
  );
};

export default Devices;
