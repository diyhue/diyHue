import React, { useEffect, useState } from "react";
import axios from "axios";
import Light from "./Light";

export default function Lights() {
  const [lights, setLights] = useState({});

  const [fetchApi, setFecthApi] = useState(true);

  useEffect(() => {
    if (fetchApi) {
      axios
        .get(
          "http://localhost/api/2bc557f6899a11ebbe303a2125f6810c/groups"
        )
        .then((fetchedLights) => {
          setLights(fetchedLights.data);
          setFecthApi(false);
        });
    }
  }, [fetchApi]);

  return (
    <div class="content">

  <div class="cardGrid">
        {Object.entries(lights).map((light) => (
          <Light setFecthApi={setFecthApi} light={light[1]} id={light[0]} />
        ))}
    </div>
    </div>
  );
}
