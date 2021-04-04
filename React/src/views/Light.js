import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Light({ setFecthApi, light, id }) {
  useEffect(() => {
    if (light.state !== undefined) {
      //console.log(light.state.on);
    }
  }, [light]);

  const [showContainer, setShowContainer] = useState(false);

  const switchLight = (id) => {
    axios
      .put(
        `http://localhost/api/2bc557f6899a11ebbe303a2125f6810c/groups/${id}/action`,
        { on: !light.state.on }
      )
      .then(() => {
        setFecthApi(true);
      });
  };

  return (
    <div className="groupContainer textLight">
    <div className="groupContainer textLight">
      <div className="iconContainer">
        <i className="fas fa-lightbulb"></i>
      </div>
      <div className="textContainer">
      <p>{light.name}</p>
      <p className="sub">3/10</p>
      </div>
      <div className="switchContainer">
            <label className="switch">
              <input className="checkbox"/>
              <span className="slider"></span>
            </label>
          </div>
      <div className="slideContainer">
        <input type="range" min="1" max="100" value="50" class="slider" id="myRange"/>
      </div>
    </div>
    </div>
  );
}
