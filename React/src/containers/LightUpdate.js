import {  MdSystemUpdate } from "react-icons/md";
import axios from "axios";
import { confirmAlert } from "react-confirm-alert"; // Import
import "react-confirm-alert/src/react-confirm-alert.css"; // Import css

const LightUpdate = ({ light }) => {
  const updateAlert = () => {
    confirmAlert({
      title: "Update light " + light["name"] + " firmware?",
      message: "Are you sure to do this?",
      buttons: [
        {
          label: "Yes",
          onClick: () => UpdateLight(),
        },
        {
          label: "No",
        },
      ],
    });
  };

  const UpdateLight = () => {}



  return (
    <>
      {['native_single', 'native_multi'].includes(light["protocol"]) &&
        <div className="btn blue"><MdSystemUpdate title="Update" onClick={() => updateAlert()} /></div>
      }

    </>


  );
};

export default LightUpdate;
