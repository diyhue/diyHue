import { useState } from "react";
import axios from "axios";
import {cieToRgb, colorTemperatureToRgb } from "../color";
import { FaLightbulb } from "react-icons/fa";

const Light = ({ user, id, light }) => {

  const switchLight = (newState) => {
  console.log('Apply state ' + JSON.stringify(newState));
  axios
    .put(
      `/api/${user}/lights/${id}/state`,
      newState
    )
  };

  const [state, setState] = useState(light.state)

  const getStyle = () => {
    let lightBg;
    if (state['colormode'] === 'xy') {
      lightBg = cieToRgb(state['xy'][0], state['xy'][1], 254)
    } else if (state['colormode'] === 'ct') {
      lightBg = colorTemperatureToRgb(state['ct'])
    }
    else {
      lightBg = 'linear-gradient(90deg, rgba(255,212,93,1))';
    }
    return { background: lightBg};
  }

  return (
      <div className={`lightContainer ${state['on'] ? 'textDark' : 'textLight'}`} style={getStyle()}>
          <div className="iconContainer">
            <FaLightbulb/>
          </div>
          <div className="textContainer">
          <p>{ light.name }</p>
          </div>
          <div className="switchContainer">
            <label className="switch">
              <input type="checkbox"
                defaultChecked={state['on']}
                onChange={(e) => switchLight({'on': e.currentTarget.checked})}
              />
              <span className="slider"></span>
            </label>
          </div>
          <div className="slideContainer">
            <input type="range" min="1" max="254" defaultValue="50" className="slider"
              onChange={(e) => switchLight({'bri': e.currentTarget.value})}
            />
          </div>
        </div>
  )
}

export default Light
