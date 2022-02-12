import { MdDeleteForever } from "react-icons/md";
import { FaMagic } from "react-icons/fa";
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
        //console.log(fetchedData.data);
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
        //console.log(fetchedData.data);
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
    //console.log(battery);
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
    <div className="card device">
      <div className="row1">
        <div className="icon">
          <FaMagic />
        </div>
        <div className="text">{device["name"]}</div>
      </div>
      <div className="row2">
        <div className="text">
          {"battery" in device["config"] && batteryLevel()}
          ModelID: {device["modelid"]} <br />
          Type: {device["type"]} <br />
          Protocol: {device["protocol"]} <br />
        </div>
      </div>
      <div className="row3">
        <div className="dropdown"></div>{" "}
        {/* replace with dropdown form, (styling missing)*/}
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
        <div className="btn red">
          <MdDeleteForever title="Delete" onClick={() => deleteAlert()} />
        </div>
      </div>
    </div>
  );
};

export default Device;
