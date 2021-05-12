import React, { useEffect, useState } from "react";
import axios from "axios";
import Light from "../containers/Light";
import Flash from "../containers/Flash"

export default function Groups({API_KEY}) {

  const [lights, setLights] = useState({});
  const [modelIds, setModelIds] = useState([]);
  const [type, setType] = useState('none');
  const [message, setMessage] = useState('no message');

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

  const fetchModelIds = () => {
    if (API_KEY !== undefined ) {
      axios
      .get(`/light-types`)
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setModelIds(fetchedData.data['result']);
      }).catch((error) => {console.error(error)});
    }
  }


  useEffect(() => {
    fetchConfig();
    fetchModelIds();
    const interval = setInterval(() => {
      fetchConfig();
    }, 2000); // <<-- ⏱ 1000ms = 1s
    return () => clearInterval(interval);
  }, [API_KEY]);

  return (
    <div className="content">
      {type !== 'none' && <Flash type={type} message={message} duration="5000" setType={setType} />}
      <div className="cardGrid">
        {Object.entries(lights).map(([id, light]) => (
            <Light
              key={id}
              api_key={API_KEY}
              id={id}
              light={light}
              modelIds={modelIds}
              setType={setType}
              setMessage={setMessage}
            />
        ))}
        </div>
      </div>
    );
  }
