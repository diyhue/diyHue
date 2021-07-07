import { MdDeleteForever } from "react-icons/md";
import {
  TiBatteryLow,
  TiBatteryMid,
  TiBatteryHigh,
  TiBatteryFull,
} from "react-icons/ti";

import axios from "axios";
import { confirmAlert } from "react-confirm-alert"; // Import
import "react-confirm-alert/src/react-confirm-alert.css"; // Import css

const Device = ({ HOST_IP, api_key, id, device, setType, setMessage }) => {
  const deleteAlert = () => {
    confirmAlert({
      title: "Delete device " + device["name"],
      message: "Are you sure to do this?",
      buttons: [
        {
          label: "Yes",
          onClick: () => deleteDevice(),
        },
        {
          label: "No",
        },
      ],
    });
  };

  const deleteDevice = () => {
    axios
      .delete(`${HOST_IP}/api/${api_key}/sensors/${id}`)
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage("Device successfully deleted");
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

  const toggleDevice = (state) => {
    axios
      .put(`${HOST_IP}/api/${api_key}/sensors/${id}/config`, { on: state })
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage(
          device["name"] + " successfully " + (state ? "enabled" : "disabled")
        );
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

  const batteryLevel = () => {
    let battery = device["config"]["battery"];
    let battryLevel = battery + "%";
    console.log(battery);
    if (battery > 90) {
      return <TiBatteryFull title={battryLevel} />;
    } else if (battery > 70) {
      return <TiBatteryHigh title={battryLevel} />;
    } else if (battery > 40) {
      return <TiBatteryMid title={battryLevel} />;
    } else {
      return <TiBatteryLow title={battryLevel} />;
    }
  };

  return (
    <>
      {device["name"]} <br />
      <div className="switchContainer">
        <label className="switch">
          <input
            type="checkbox"
            defaultChecked={device["config"]["on"]}
            onChange={(e) => toggleDevice(e.currentTarget.checked)}
          />
          <span className="slider"></span>
        </label>
      </div>
      Protocol: {device["protocol"]}
      <br />
      {"battery" in device["config"] && batteryLevel()}
      <MdDeleteForever title="Delete" onClick={() => deleteAlert()} />
      <br />
      <br />
    </>
  );
};

export default Device;
