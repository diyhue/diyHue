import React, { useEffect, useState } from "react";
import axios from "axios";
import Light from "../containers/Light";
import AddLight from "../containers/AddLight";
import Flash from "../containers/Flash"

export default function Groups({ API_KEY }) {

  const [lights, setLights] = useState({});
  const [modelIds, setModelIds] = useState([]);
  const [type, setType] = useState('none');
  const [message, setMessage] = useState('no message');
  const [lightForm, setLightForm] = useState(false);

  const fetchLights = () => {
    if (API_KEY !== undefined) {
      axios
        .get(`/lights`)
        .then((fetchedData) => {
          console.log(fetchedData.data);
          setLights(fetchedData.data);
        }).catch((error) => { console.error(error) });
    }
  }

  const searchForLights = () => {
    if (API_KEY !== undefined) {
      axios
        .post(`/api/${API_KEY}/lights`, "")
        .then((fetchedData) => {
          console.log(fetchedData.data);
          setMessage('Searching for new lights...');
          setType('none');
          setType('success');
        }).catch((error) => {
          console.error(error)
          setMessage('Error occured, check browser console');
          setType('none');
          setType('error');
        });
    };
  }

  const fetchModelIds = () => {
    if (API_KEY !== undefined) {
      axios
        .get(`/light-types`)
        .then((fetchedData) => {
          console.log(fetchedData.data);
          setModelIds(fetchedData.data['result']);
        }).catch((error) => { console.error(error) });
    }
  }


  useEffect(() => {
    fetchLights();
    fetchModelIds();
    const interval = setInterval(() => {
      fetchLights();
    }, 2000); // <<-- ⏱ 1000ms = 1s
    return () => clearInterval(interval);
  }, [API_KEY]);

  return (
    <div className="content">
      {type !== 'none' && <Flash type={type} message={message} duration="5000" setType={setType} />}
      <div className="cardGrid">
        <div className="linkbtn" onClick={() => searchForLights()}>Scan For Lights
        <div className='btn btn-block'></div></div>
        <a onClick={() => setLightForm(!lightForm)} className="someClassWithCursorPointer">Add light manually</a>
        {lightForm && <AddLight API_KEY={API_KEY}  ></AddLight>}
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
