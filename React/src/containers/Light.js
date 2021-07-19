import { FaLightbulb, FaCheck } from "react-icons/fa";
import { MdDeleteForever, MdSystemUpdate } from "react-icons/md";
import { RiAlertLine } from "react-icons/ri";
import axios from "axios";
import Dropdown from "react-dropdown";
import "react-dropdown/style.css";
import { confirmAlert } from "react-confirm-alert"; // Import
import "react-confirm-alert/src/react-confirm-alert.css"; // Import css

const Light = ({
  HOST_IP,
  api_key,
  id,
  light,
  modelIds,
  setType,
  setMessage,
}) => {
  const deleteAlert = () => {
    confirmAlert({
      title: "Delete light " + light["name"],
      message: "Are you sure to do this?",
      buttons: [
        {
          label: "Yes",
          onClick: () => deleteLight(),
        },
        {
          label: "No",
        },
      ],
    });
  };

  const deleteLight = () => {
    axios
      .delete(`${HOST_IP}/api/${api_key}/lights/${id}`)
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage("Light successfully deleted");
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

  const alertLight = () => {
    axios
      .put(`${HOST_IP}/api/${api_key}/lights/${id}/state`, { alert: "select" })
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage("Light alerted");
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

  const setModelId = (modelid) => {
    console.log({ [id]: modelid });
    axios
      .post(`${HOST_IP}/light-types`, { [id]: modelid })
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage("Modelid updated");
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
      <div className="card light expanded">
      <div className="row1">
        <div className="icon"><FaLightbulb onClick={() => alertLight()} /></div>
        <div className="text">{light["name"]}{" "}</div>
      
      </div>
      <div className="row3">
      <Dropdown
        options={modelIds}
        value={light["modelid"]}
        onChange={(e) => setModelId(e.value)}
        placeholder="Choose light modelid"
      />
        <div className="btn blue"><MdSystemUpdate title="Update" /></div>
        <div className="btn red"><MdDeleteForever title="Delete" onClick={() => deleteAlert()} />{" "}</div>
      </div>
      <div className="row4">
        <ul>
          <li>Protocol: {light["protocol"]}</li>
          <li>IP: {light["protocol_cfg"]["ip"]}</li>
        </ul>
      </div>

      {(light["state"]["reachable"] || <div className="label">Offline</div>)}

      </div> 


  );
};

export default Light;
