import React, { useEffect, useState } from "react";
import axios from "axios";
import Group from "../containers/Group"

export default function Groups() {

  const [config, setConfig] = useState({ config: {}, lights: {}, groups: {}, scenes: {}});

  const [groupState, setgroupState] = useState(false);

  useEffect(() => {
    axios
      .get("http://localhost/api/local")
      .then((fetchedData) => {
        setConfig(fetchedData.data);
      });
  }, [groupState]);

  const switchLight = (state) => {
    console.log(`Current State is: ${state}`, `Switchting to ${!state}`);
    setgroupState(!state);
  };

  return (
  <div className="content">
    <div className="cardGrid">
      {Object.entries(config.groups).filter(group => group[1].type !== 'Entertainment').map(([id, group]) => (
          <Group
            key={id}
            user={Object.keys(config.config['whitelist'])[0]}
            id={id}
            group={group}
            groupState={groupState}
            setgroupState={setgroupState}
            lights={config.lights}
            scenes={config.scenes}
          />
      ))}
      </div>
    </div>
  );
}
