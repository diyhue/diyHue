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
        `http://localhost/api/2bc557f6899a11ebbe303a2125f6810c/lights/${id}/state`,
        { on: !light.state.on }
      )
      .then(() => {
        setFecthApi(true);
      });
  };

  return (
    <div className="lightCard">
      <div className="name">{light.name}</div>
      <div className="button">
        <button
          onClick={() => {
            switchLight(id);
          }}
        >
          Switch Light
        </button>
        <br />
        <button
          onClick={() => {
            setShowContainer(!showContainer);
          }}
        >
          Show secret text
        </button>
        <div className={showContainer ? "container show" : "container"}>
          Secret Text
        </div>
      </div>
    </div>
  );
}
