import React, { useEffect, useState } from "react";
import axios from "axios";
import TheLayout from "./containers/TheLayout";

import "./scss/mainframe.scss";
import "./scss/components.scss";
import "./scss/content.scss";
import "./scss/forms.scss";
import "./scss/groups.scss";
import "./scss/notification.scss";
import "./scss/modal.scss";
import "./scss/scenepicker.scss";
import "./scss/device.scss";

const loading = (
  <div className="pt-3 text-center">
    <div className="sk-spinner sk-spinner-pulse"></div>
  </div>
);

const App = () => {
  const [API_KEY, setAPI_KEY] = useState();

  const HOST_IP = ""; // Pass the IP (http://x.x.x.x) of the diyHue Bridge, if running through npm start

  useEffect(() => {
    //console.log(`${HOST_IP}/get-key`);
    axios
      .get(`${HOST_IP}/get-key`)
      .then((result) => {
        if (typeof result.data === "string" && result.data.length === 32) {
          //console.log(`API_KEY from API: ${result.data}`);
          setAPI_KEY(result.data);
        } else {
          console.log(`Unable to fetch API_KEY! from ${HOST_IP}/get-key`);
        }
      })
      .catch((error) => {
        console.error(error);
      });
  }, []);

  return (
    <React.Suspense fallback={loading}>
      <TheLayout HOST_IP={HOST_IP} API_KEY={API_KEY} />
    </React.Suspense>
  );
};

export default App;
