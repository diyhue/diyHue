import { useState, useEffect } from "react";
import { FaBars } from "react-icons/fa";
import axios from "axios";
import { motion } from "framer-motion";

const TheHeader = ({ HOST_IP, showSidebar, setShowSidebar, API_KEY }) => {
  const [group0State, setGroup0State] = useState(false);

  const iconVariants = {
    opened: {
      rotate: 90,
      //scale: 2
    },
    closed: {
      rotate: 0,
      //scale: 1
    },
  };

  useEffect(() => {
    const fetchGroups = () => {
      if (API_KEY !== undefined) {
        axios
          .get(`${HOST_IP}/api/${API_KEY}/groups/0`)
          .then((fetchedData) => {
            //console.log(fetchedData.data);
            setGroup0State(fetchedData.data["state"]["any_on"]);
          })
          .catch((error) => {
            console.error(error);
          });
      }
    };

    fetchGroups();
    const interval = setInterval(() => {
      fetchGroups();
    }, 5000); // <<-- ⏱ 1000ms = 1s
    return () => clearInterval(interval);
  }, [HOST_IP, API_KEY]);

  const handleToggleChange = (state) => {
    const newState = { on: state };
    setGroup0State(state);
    console.log("Apply state " + JSON.stringify(newState));
    axios.put(`${HOST_IP}/api/${API_KEY}/groups/0/action`, newState);
  };

  return (
    <div className="topbarRight">
      <motion.div
        className="hamburger"
        initial={false}
        variants={iconVariants}
        animate={showSidebar ? "opened" : "closed"}
        onClick={() => setShowSidebar(!showSidebar)}
      >
        <FaBars />
      </motion.div>
      <div className="onbtn">
        <p>Turn all lights {group0State ? "off" : "on"}</p>
        <div className="switchContainer">
          <label className="switch">
            <input
              type="checkbox"
              value={group0State}
              onChange={(e) => handleToggleChange(e.target.checked)}
              checked={group0State}
            />
            <span className="slider"></span>
          </label>
        </div>
      </div>
    </div>
  );
};

export default TheHeader;
