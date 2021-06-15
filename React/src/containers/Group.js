import { FaCaretLeft, FaList  ,  FaPalette, FaTint, FaCouch} from "react-icons/fa";
import { useState } from "react";
import axios from "axios";
import Scenes from "./Scenes"
import Light from "./GroupLight"
import ColorPicker from "./ColorPicker"
import {cieToRgb, colorTemperatureToRgb } from "../color";

const Group = ({api_key, id, group, lights, scenes}) => {

  const [showContainer, setShowContainer] = useState('closed');

  const handleToggleChange = (state) => {
    const newState = {'on': state};
    group.state['any_on'] = state;
    console.log('Apply state ' + JSON.stringify(newState));
    axios.put(`/api/${api_key}/groups/${id}/action`, newState);
  }

  const handleBriChange = (state) => {
    const newState = {'bri': state};
    group.action['bri'] = state;
    console.log('Apply state ' + JSON.stringify(newState));
    axios.put(`/api/${api_key}/groups/${id}/action`, newState);
  }

  const getStyle = () => {
    if (group.state['any_on']) {
      let lightBg = 'linear-gradient(90deg, ';
      let step = 100 / group["lights"].length;
      for (const [index, light] of group.lights.entries()) {
        if (lights[light]['state']['colormode'] === 'xy') {
          if (group["lights"].length === 1) {
            lightBg = lightBg + 'rgba(200,200,200,1) 0%,'; 
          }
          lightBg = lightBg + cieToRgb(lights[light]['state']['xy'][0], lights[light]['state']['xy'][1], 254) + ' ' + Math.floor(step * (index + 1)) + '%,';
        } else if (lights[light]['state']['colormode'] === 'ct') {
          if (group["lights"].length === 1) {
            lightBg = lightBg + 'rgba(200,200,200,1) 0%,'; 
          }
          lightBg = lightBg + colorTemperatureToRgb(lights[light]['state']['ct']) + ' ' + Math.floor(step * (index + 1)) + '%,';
        }
        else {
          if (group["lights"].length === 1) {
            lightBg = lightBg + 'rgba(200,200,200,1) 0%,'; 
          }
          lightBg = lightBg + 'rgba(255,212,93,1) ' + Math.floor(step * (index + 1)) + '%,';
        }
      }
      return { background: lightBg.slice(0, -1) + ')' };
    }
  }


  return (
    <div className={`groupContainer ${group.state['any_on'] ? 'textDark' : 'textLight'} ${showContainer !== 'closed' ? 'expanded' : ''}`} style={getStyle()}>
      {showContainer !== 'closed' &&
        <div className="header">
          <div onClick={() => setShowContainer('closed')}>
          <div className="icon"><FaCaretLeft/></div>
          <div className="text">close</div>
        </div>
        <div className={`tab ${showContainer === 'lights' ? 'active' : ''}`} onClick={() => setShowContainer('lights')}><FaList/></div>
        <div className={`tab ${showContainer === 'scenes' ? 'active' : ''}`} onClick={() => setShowContainer('scenes')}><FaPalette/></div>
        <div className={`tab ${showContainer === 'colorPicker' ? 'active' : ''}`} onClick={() => setShowContainer('colorPicker')}><FaTint/></div>
      </div>}
      <div className="overlayBtn" onClick={() => setShowContainer('colorPicker')}></div>
      <div className="iconContainer">
        <FaCouch/>
      </div>
      <div className="textContainer">
        <p>{group.name}</p>
      </div>
      <div className="switchContainer">
        <label className="switch">
          <input type="checkbox"
            value={group.state['any_on']}
            checked={group.state['any_on']}
            onChange={(e) => handleToggleChange(e.target.checked)}
          />
          <span className="slider"></span>
        </label>
      </div>
      <div className="slideContainer">
        <input
          type="range"
          min="1"
          max="254"
          value={group.action['bri']}
          step="1"
          className="slider"
          onChange={(e) => handleBriChange(parseInt(e.target.value))}
        />
      </div>
      <div className="dimmer">
        {showContainer === 'scenes' && <Scenes
          api_key={api_key}
          groupId={id}
          scenes={ scenes }
        />}
        {showContainer === 'lights' &&
        <div className="lightsContainer">
          {group.lights.map((light) => (<Light
            api_key={api_key}
            key={light}
            id={light}
            light={lights[light]}
          />
          ))}
        </div>}
        {showContainer === 'colorPicker' && <ColorPicker
            api_key={api_key}
            lights={ lights }
            groupLights = { group.lights }
        />}
      </div>
    </div>
  )
}

export default Group
