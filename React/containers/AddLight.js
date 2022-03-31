import { useState } from "react";
import axios from "axios";
import Dropdown from "react-dropdown";
import "react-dropdown/style.css";

const AddLight = ({ setType, setMessage, HOST_IP, API_KEY }) => {
  const [lightData, setLightData] = useState({
    protocol: "auto",
  });

  const handleChange = (key, value) => {
    setLightData({
      ...lightData,
      [key]: value,
    });
  };

  const handleForm = (evt) => {
    evt.preventDefault();
    const { protocol: lightproto, ip: lightip, ...rest } = lightData;
    const formattedData = {
      protocol: lightproto,
      ip: lightip,
      config: rest,
    };
    axios.post(`${HOST_IP}/api/${API_KEY}/lights`, formattedData);
    setMessage("Light added");
    setType("none");
    setType("success");
  };

  const protocols = [
    { value: "auto", label: "Autodetect" },
    { value: "domoticz", label: "Domoticz" },
    { value: "flex", label: "Flex" },
    { value: "jeedom", label: "Jeedom" },
    { value: "milight", label: "MiLight" },
    { value: "mibox", label: "Mi Box" },
    { value: "wiz", label: "Wiz" },
  ];

  const milightGroups = ["1", "2", "3", "4"];

  const milightModes = [
    { value: "rgbw", label: "RGBW" },
    { value: "cct", label: "CCT" },
    { value: "rgb_cct", label: "RGB-CCT" },
    { value: "rgb", label: "RGB" },
  ];

  const lightModelIds = [
    { value: "LOM001", label: "On/Off Plug" },
    { value: "LWB010", label: "Dimmable Light" },
    { value: "LTW001", label: "Color temperature Light" },
    { value: "LCT015", label: "Color Light" },
    { value: "LST002", label: "Color Strip" },
  ];

  return (
    <form onSubmit={(e) => handleForm(e)} className="add-form">
      <div className="form-control">
      <label>Protocol:</label>
      <Dropdown
        options={protocols}
        value={lightData.protocol}
        // On Dropdown component use e.value
        onChange={(e) => handleChange("protocol", e.value)}
        placeholder="Choose light protocol"
      />
      </div>
      <div className="form-control">
        <label>Light IP Address:</label>
        <input
          type="text"
          placeholder="192.168.x.x"
          value={lightData.ip}
          // On regular HTML input components use e.taget.value
          onChange={(e) => handleChange("ip", e.target.value)}
        />
      </div>
      {lightData.protocol !== "auto" && (
        <>
          <div className="form-control">
            <label>Name</label>
            <input
              type="text"
              value={lightData.lightName}
              onChange={(e) => handleChange("lightName", e.target.value)}
              placeholder="Name used on diyhue"
            />
          </div>
          <div className="form-control">
            <Dropdown
              options={lightModelIds}
              value={lightData.lightModelID}
              onChange={(e) => handleChange("lightModelID", e.value)}
              placeholder="Emulated light type"
            />
          </div>
        </>
      )}
      {(lightData.protocol === "milight" || lightData.protocol === "mibox") && (
        <>
          <div className="form-control">
            <label>Device ID</label>
            <input
              type="text"
              value={lightData.miID}
              onChange={(e) => handleChange("miID", e.target.value)}
              placeholder="0x1234"
            />
          </div>
          <Dropdown
            options={milightModes}
            value={lightData.miModes}
            onChange={(e) => handleChange("miModes", e.value)}
            placeholder="Choose light mode"
          />
          <Dropdown
            options={milightGroups}
            value={lightData.miGroups}
            onChange={(e) => handleChange("miGroups", e.value)}
            placeholder="Choose light group"
          />
        </>
      )}
      {lightData.protocol === "mibox" && (
        <div className="form-control">
          <label>Port</label>
          <input
            type="number"
            placeholder="Mi Box port"
            value={lightData.miBoxPort}
            onChange={(e) => handleChange("miboxPort", e.target.value)}
          />
        </div>
      )}
      {lightData.protocol === "domoticz" && (
        <div className="form-control">
          <label>Device ID</label>
          <input
            type="text"
            placeholder=""
            value={lightData.domoticzID}
            onChange={(e) => handleChange("domoticzID", e.target.value)}
          />
        </div>
      )}
      {lightData.protocol === "jeedom" && (
        <>
          <div className="form-control">
            <label>Light Api</label>
            <input
              type="text"
              placeholder="Light Api"
              value={lightData.jeedomlightAPI}
              onChange={(e) => handleChange("jeedomlightAPI", e.target.value)}
            />
          </div>
          <div className="form-control">
            <label>Light ID</label>
            <input
              type="text"
              placeholder="Light ID"
              value={lightData.jeedomlightID}
              onChange={(e) => handleChange("jeedomlightID", e.target.value)}
            />
          </div>
        </>
      )}
      <div className="form-control">
        <input type="submit" value="Add Light" className="btn btn-block" />
      </div>
    </form>
  );
};

export default AddLight;
