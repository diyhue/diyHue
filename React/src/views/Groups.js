import React, { useEffect, useState } from "react";
import axios from "axios";
import Group from "../containers/Group";

export default function Groups({API_KEY}) {

  const [config, setConfig] = useState({ config: {}, lights: {}, groups: {}, scenes: {}});


  const fetchConfig = () => {
    if (API_KEY !== undefined ) {
      axios
      .get(`/api/${API_KEY}`)
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setConfig(fetchedData.data);
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
      {Object.entries(config.groups).filter(group => group[1].type !== 'Entertainment').map(([id, group]) => (
          <Group
            key={id}
            api_key={API_KEY}
            id={id}
            group={group}
            lights={config.lights}
            scenes={config.scenes}
          />
      ))}
      </div>
    </div>
  );
}
