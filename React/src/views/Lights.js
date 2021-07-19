import React, { useEffect, useState } from "react";
import axios from "axios";
import Light from "../containers/Light";
import AddLight from "../containers/AddLight";
import Flash from "../containers/Flash";

export default function Lights({ HOST_IP, API_KEY }) {
  const [lights, setLights] = useState({});
  const [modelIds, setModelIds] = useState([]);
  const [type, setType] = useState("none");
  const [message, setMessage] = useState("no message");
  const [lightForm, setLightForm] = useState(false);

  const searchForLights = () => {
    if (API_KEY !== undefined) {
      axios
        .post(`${HOST_IP}/api/${API_KEY}/lights`, "")
        .then((fetchedData) => {
          console.log(fetchedData.data);
          setMessage("Searching for new lights...");
          setType("none");
          setType("success");
        })
        .catch((error) => {
          console.error(error);
          setMessage("Error occured, check browser console");
          setType("none");
          setType("error");
        });
    }
  };

  useEffect(() => {
    const fetchLights = () => {
      if (API_KEY !== undefined) {
        axios
          .get(`${HOST_IP}/lights`)
          .then((fetchedData) => {
            console.log(fetchedData.data);
            setLights(fetchedData.data);
          })
          .catch((error) => {
            console.error(error);
          });
      }
    };

    const fetchModelIds = () => {
      if (API_KEY !== undefined) {
        axios
          .get(`${HOST_IP}/light-types`)
          .then((fetchedData) => {
            console.log(fetchedData.data);
            setModelIds(fetchedData.data["result"]);
          })
          .catch((error) => {
            console.error(error);
          });
      }
    };

    fetchLights();
    fetchModelIds();
    const interval = setInterval(() => {
      fetchLights();
    }, 2000); // <<-- ⏱ 1000ms = 1s
    return () => clearInterval(interval);
  }, [HOST_IP, API_KEY]);

  return (
    <div className="content">
      {type !== "none" && (
        <Flash
          type={type}
          message={message}
          duration="5000"
          setType={setType}
        />
      )}
      <div className="cardGrid">
        <div className="btn generic" onClick={() => searchForLights()}>
          Scan For Lights
          <div className="btn btn-block"></div>
        </div>
        <button
          onClick={() => setLightForm(!lightForm)}
          className="generic"
          style={{}}
        >
          Add light manually
        </button>
        {lightForm && <AddLight 
                        setType={setType}
                        setMessage={setMessage} 
                        HOST_IP={HOST_IP} 
                        API_KEY={API_KEY}>
                      </AddLight>}
                      </div>
      <div className="cardGrid">
        {Object.entries(lights).map(([id, light]) => (
          <Light
            key={id}
            HOST_IP={HOST_IP}
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
