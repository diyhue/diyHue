import React, { useEffect, useState } from "react";
import axios from "axios";
import TheLayout from "./containers/TheLayout";

import "./scss/style.scss";

const loading = (
  <div className="pt-3 text-center">
    <div className="sk-spinner sk-spinner-pulse"></div>
  </div>
);

const App = () => {
  const [API_KEY, setAPI_KEY] = useState();

  const HOST_IP = "http://localhost"; // Pass the IP of the diyHue Bridge, if running through npm start

  useEffect(() => {
    axios
      .get(`${HOST_IP}/get-key`)
      .then((result) => {
        if (typeof result.data === "string" && result.data.length === 32) {
          console.log(`API_KEY from API: ${result.data}`);
          setAPI_KEY(result.data);
        } else {
          console.log("Unable to fetch API_KEY!");
        }
      })
      .catch((error) => {
        console.error(error);
      });
  }, []);

  return (
    <React.Suspense fallback={loading}>
      <div className="flexContainer">
        <TheLayout HOST_IP={HOST_IP} API_KEY={API_KEY} />
      </div>
    </React.Suspense>
  );
};

export default App;
