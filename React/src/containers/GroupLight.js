import { useState } from "react";
import { RiAlertLine } from "react-icons/ri";
import axios from "axios";
import {cieToRgb, colorTemperatureToRgb } from "../color";
import { FaLightbulb } from "react-icons/fa";

const Light = ({ api_key, id, light }) => {

  const switchLight = (newState) => {
  console.log('Apply state ' + JSON.stringify(newState));
  axios
    .put(
      `/api/${api_key}/lights/${id}/state`,
      newState
    )
  };

  const getStyle = () => {

    if (light['state']['on']) {
      let lightBg;
      if (light['state']['colormode'] === 'xy') {
        lightBg = cieToRgb(light['state']['xy'][0], light['state']['xy'][1], 254)
      } else if (light['state']['colormode'] === 'ct') {
        lightBg = colorTemperatureToRgb(light['state']['ct'])
      }
      else {
        lightBg = 'linear-gradient(90deg, rgba(255,212,93,1))';
      }
      return { background: lightBg};
    }
  }

  return (
      <div className={`lightContainer ${light['state']['on'] ? 'textDark' : 'textLight'}`} style={getStyle()}>
          <div className="iconContainer">
            <FaLightbulb/>
          </div>
          <div className="textContainer">
          <p>{ light.name } {light['state']['reachable'] || <RiAlertLine title='Unrechable'/>}</p>
          </div>
          <div className="switchContainer">
            <label className="switch">
              <input type="checkbox"
                defaultChecked={light['state']['on']}
                onChange={(e) => switchLight({'on': e.currentTarget.checked})}
              />
              <span className="slider"></span>
            </label>
          </div>
          <div className="slideContainer">
            <input type="range" min="1" max="254" defaultValue="50" className="slider"
              onChange={(e) => switchLight({'bri': parseInt(e.currentTarget.value)})}
            />
          </div>
        </div>
  )
}

export default Light
