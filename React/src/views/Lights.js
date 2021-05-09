import React, { useEffect, useState } from "react";
import axios from "axios";
import Light from "../containers/Light";

export default function Groups({API_KEY}) {

  const [lights, setLights] = useState({});


  const fetchConfig = () => {
    if (API_KEY !== undefined ) {
      axios
      .get(`/lights`)
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setLights(fetchedData.data);
      }).catch((error) => {console.error(error)});
    }
  }


  useEffect(() => {
    fetchConfig();
    const interval = setInterval(() => {
      fetchConfig();
    }, 2000); // <<-- ⏱ 1000ms = 1s
    return () => clearInterval(interval);
  }, [API_KEY]);

  return (
  <div className="content">
    <div className="cardGrid">
      {Object.entries(lights).map(([id, light]) => (
          <Light
            key={id}
            api_key={API_KEY}
            id={id}
            light={light}
          />
      ))}
      </div>
    </div>
  );
}
