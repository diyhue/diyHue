import React, { useEffect, useState } from "react";
import axios from "axios";
import Group from "../containers/Group";

export default function Groups() {

  const [config, setConfig] = useState({ config: {}, lights: {}, groups: {}, scenes: {}});

  const [API_KEY, setAPI_KEY] = useState();

  useEffect(() => {
    axios.get("/get-key").then((result) => {
      if (typeof result.data === "string" && result.data.length === 32) {
        console.log(`API_KEY from API: ${result.data}`);
        setAPI_KEY(result.data);
      } else {
        // 🔥 TODO: Promt an error when the reseived data is not the key
        //         E.g. alert("Not Authorized");
        setAPI_KEY("12345678901234567890123456789012");
      }
      console.log("debug 1")
      fetchConfig(); // 🔥 TODO: Move this call inside the above if statement - so that it is onyl fetching when there is a key
    }).catch((error) => {console.error(error)});
  }, []);

  const fetchConfig = () => {
    console.log("fetch")
    if (API_KEY !== undefined) {
      axios
        .get(`/api/${API_KEY}`)
        .then((fetchedData) => {
          console.log(fetchedData.data);
          setConfig(fetchedData.data);
        }).catch((error) => {console.error(error)});
    }
  }

  useEffect(() => {
    const interval = setInterval(() => {
      if (API_KEY !== undefined) {
        console.log("debug 2")
        fetchConfig();
      } else {
        console.log("No Key");
      }
    }, 1000); // <<-- ⏱ 1000ms = 1s
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
