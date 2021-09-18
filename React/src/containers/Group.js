import {
  FaCouch,
  FaChevronDown,
  FaChevronUp,
  FaImages,
  FaLightbulb,
  FaPalette

} from "react-icons/fa";
import { BsFillHouseDoorFill } from "react-icons/bs";
import { MdInvertColors } from "react-icons/md";
import { useState } from "react";
import axios from "axios";
import Scenes from "./Scenes";
import Light from "./GroupLight";
import ColorPicker from "./ColorPicker";
import ColorTempPicker from "./ColorTempPicker";
import debounce from 'lodash.debounce';
import { motion, AnimateSharedLayout, AnimatePresence } from "framer-motion"
import { cieToRgb, colorTemperatureToRgb } from "../color";


const Group = ({ HOST_IP, api_key, id, group, lights, scenes }) => {
  const [showContainer, setShowContainer] = useState("closed");
  const [sceneModal, setSceneModal] = useState(false);

  const handleToggleChange = (state) => {
    const newState = { on: state };
    group.state["any_on"] = state;
    console.log("Apply state " + JSON.stringify(newState));
    axios.put(`${HOST_IP}/api/${api_key}/groups/${id}/action`, newState);
  };

  const handleBriChange = (state) => {
    const newState = { bri: state };
    group.action["bri"] = state;
    console.log("Apply state " + JSON.stringify(newState));
    axios.put(`${HOST_IP}/api/${api_key}/groups/${id}/action`, newState);
  };

  const onlineLights = () => {
    let counter = 0;
    for (const [index, light] of group.lights.entries()) {
      if (lights[light]["state"]["reachable"] === true)
        counter = counter + 1;
    }
    return counter;
  }

  const getStyle = () => {
    if (group.state["any_on"]) {
      let lightBg = "linear-gradient(45deg, ";
      let step = 100 / group["lights"].length;
      for (const [index, light] of group.lights.entries()) {
        if (lights[light]["state"]["colormode"] === "xy") {
          if (group["lights"].length === 1) {
            lightBg = lightBg + "rgba(200,200,200,1) 0%,";
          }
          lightBg =
            lightBg +
            cieToRgb(
              lights[light]["state"]["xy"][0],
              lights[light]["state"]["xy"][1],
              254
            ) +
            " " +
            Math.floor(step * (index + 1)) +
            "%,";
        } else if (lights[light]["state"]["colormode"] === "ct") {
          if (group["lights"].length === 1) {
            lightBg = lightBg + "rgba(200,200,200,1) 0%,";
          }
          lightBg =
            lightBg +
            colorTemperatureToRgb(lights[light]["state"]["ct"]) +
            " " +
            Math.floor(step * (index + 1)) +
            "%,";
        } else {
          if (group["lights"].length === 1) {
            lightBg = lightBg + "rgba(200,200,200,1) 0%,";
          }
          lightBg =
            lightBg +
            "rgba(255,212,93,1) " +
            Math.floor(step * (index + 1)) +
            "%,";
        }
      }
      return { background: lightBg.slice(0, -1) + ")" };
    }
  };

  return (
    <div className="groupCard">
      <Scenes
        HOST_IP={HOST_IP}
        api_key={api_key}
        groupId={id}
        scenes={scenes}
        sceneModal={sceneModal}
        setSceneModal={setSceneModal}
      />
      <div className="row top">
        <div className="gradient" style={getStyle()} >{group["type"] === "Zone" ? <FaCouch style={{ color: "#8400FF" }} /> : <BsFillHouseDoorFill style={{ color: "#8400FF" }} />}</div>
        <div className="text">
          <p className="name">{group.name}</p>
          <p className="subtext">{onlineLights()} lamps online</p></div>
        <div className="switchContainer">
          <label className="switch">
            <input
              type="checkbox"
              value={group.state["any_on"]}
              checked={group.state["any_on"]}
              onChange={(e) => handleToggleChange(e.target.checked)}
            />
            <span className="slider"></span>
          </label>
        </div>
      </div>
      <div className="row background">
        <div className="sliderContainer">
          <input
            type="range"
            min="1"
            max="254"
            value={group.action["bri"]}
            step="1"
            className="slider"
            onChange={(e) => handleBriChange(parseInt(e.target.value))}
          />
        </div>
      </div>
      <AnimateSharedLayout>
        <motion.div className="row colorpicker">
          <AnimatePresence>
            {showContainer === "colorPicker" && (
              <ColorPicker
                HOST_IP={HOST_IP}
                api_key={api_key}
                lights={lights}
                groupLights={group.lights}
              />
            )}
            {showContainer === "colorTempPicker" && (
              <ColorTempPicker
                HOST_IP={HOST_IP}
                api_key={api_key}
                groupId={id}
                group={group}
              />
            )}
            {showContainer === "lights" && (
              <div className="lights">
                {group.lights.map((light) => (
                  <Light
                    HOST_IP={HOST_IP}
                    api_key={api_key}
                    key={light}
                    id={light}
                    light={lights[light]}
                  />
                ))}
              </div>
            )}
          </AnimatePresence>
        </motion.div>
      </AnimateSharedLayout>
      {showContainer === "closed" && (
        <div className="row bottom">
          <div className="expandbtn"><FaChevronDown
            onClick={() => setShowContainer("colorPicker")}
          /></div>
        </div>) ||
        (<div className="row bottom">
          <div className="btn"><FaPalette
            onClick={() => setShowContainer("colorPicker")} />
          </div>
          <div className="btn"><FaImages
            onClick={() => setSceneModal(true)}
          /></div>
          <div className="expandbtn"><FaChevronUp
            onClick={() => setShowContainer("closed")}
          /></div>
          <div className="btn"><FaLightbulb
            onClick={() => setShowContainer("lights")}
          /></div>
          <div className="btn"><MdInvertColors
            onClick={() => setShowContainer("colorTempPicker")}
          /></div>
        </div>)}



    </div>
  );
};

export default Group;



