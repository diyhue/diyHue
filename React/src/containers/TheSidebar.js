import { memo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaHome,
  FaLightbulb,
  FaLink,
  FaCog,
  FaSignOutAlt,
  FaInfoCircle,
  FaExclamationTriangle,
} from "react-icons/fa";
import { SiHomeassistant } from "react-icons/si";
import { MdSettingsRemote } from "react-icons/md";
import { Bridge } from "../icons/Bridge"
import { Zigbee } from "../icons/Zigbee"
import { Deconz } from "../icons/Deconz"
import { Diybridge } from "../icons/Diybridge"
import { Tradfri } from "../icons/Tradfri"
import logo from "../static/images/logo.svg";
import "../scss/sidebar.scss";

const TheSidebar = ({ showSidebar }) => {

  const [currentElement, setCurrentElement] = useState(window.location.hash.substring(2));
  return (
    <AnimatePresence initial={false}>
      {showSidebar && (
        <motion.div className="columnLeft"
          animate={{ width: 180 }}
          initial={{ width: 0 }}
          exit={{ width: 0 }}>
          <div className="topbarLeft active">
            <div className="logo"><img src={logo} alt="diyHue Logo" /></div>
            <div className="headline">DiyHue</div>
          </div>
          <div className="sidebar">
            <ul>
              <a href="#home">
                <li className={`${currentElement === "groups" ? "active" : ""}`}
                  onClick={() => setCurrentElement("groups")}>
                  <FaHome style={{ color: "#2BA9F0" }} /> <p>Groups</p>
                </li>
              </a>
              <a href="#lights">
                <li className={`${currentElement === "lights" ? "active" : ""}`}
                  onClick={() => setCurrentElement("lights")}>
                  <FaLightbulb style={{ color: "#4DB8B4" }} /> <p>Lights</p>
                </li>
              </a>
              <a href="#linkbutton">
                <li className={`${currentElement === "linkbutton" ? "active" : ""}`}
                  onClick={() => setCurrentElement("linkbutton")}>
                  <FaLink style={{ color: "#70C877" }} /> <p>Link Button</p>
                </li>
              </a>
              <a href="#bridge">
                <li className={`${currentElement === "bridge" ? "active" : ""}`}
                  onClick={() => setCurrentElement("bridge")}>
                  <Diybridge style={{ color: "#9CD747" }} /> <p>Bridge</p>
                </li>
              </a>
              <a href="#devices">
                <li className={`${currentElement === "devices" ? "active" : ""}`}
                  onClick={() => setCurrentElement("devices")}>
                  <MdSettingsRemote style={{ color: "#E0E043" }} /> <p>Devices</p>
                </li>
              </a>
              <a href="#mqtt">
                <li className={`${currentElement === "mqtt" ? "active" : ""}`}
                  onClick={() => setCurrentElement("mqtt")}>
                  <Zigbee style={{ color: "#FCEE86" }} /> <p>MQTT</p>
                </li>
              </a>
              <a href="#ha">
                <li className={`${currentElement === "ha" ? "active" : ""}`}
                  onClick={() => setCurrentElement("ha")}>
                  <SiHomeassistant style={{ color: "#0FFEFB" }} /> <p>HA</p>
                </li>
              </a>
              <a href="#deconz">
                <li className={`${currentElement === "deconz" ? "active" : ""}`}
                  onClick={() => setCurrentElement("deconz")}>
                  <Deconz style={{ color: "#FFFEFB" }} /> <p>Deconz</p>
                </li>
              </a>
              <a href="#tradfri">
                <li className={`${currentElement === "tradfri" ? "active" : ""}`}
                  onClick={() => setCurrentElement("tradfri")}>
                  <Tradfri style={{ color: "#EBAB94" }} />{" "}
                  <p>Tradfri</p>
                </li>
              </a>
              <a href="#hue">
                <li className={`${currentElement === "hue" ? "active" : ""}`}
                  onClick={() => setCurrentElement("hue")}>
                  <Bridge style={{ color: "#EF7B22" }} /> <p>Hue Bridge</p>
                </li>
              </a>
              <a href="#alarm">
                <li className={`${currentElement === "alarm" ? "active" : ""}`}
                  onClick={() => setCurrentElement("alarm")}>
                  <FaExclamationTriangle style={{ color: "#CD3D45" }} /> <p>Alarm</p>
                </li>
              </a>
              <a href="#settings">
                <li className={`${currentElement === "settings" ? "active" : ""}`}
                  onClick={() => setCurrentElement("settings")}>
                  <FaCog style={{ color: "#D85BCD" }} /> <p>Settings</p>
                </li>
              </a>
              <a href="#about">
                <li className={`${currentElement === "about" ? "active" : ""}`}
                  onClick={() => setCurrentElement("about")}>
                  <FaInfoCircle style={{ color: "#722371" }} /> <p>About</p>
                </li>
              </a>
              <a href="/logout">
                <li>
                  <FaSignOutAlt style={{ color: "#7E7E7E" }} /> <p>Logout</p>
                </li>
              </a>
            </ul>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default memo(TheSidebar);
