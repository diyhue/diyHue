import React from 'react'
import { FaHome, FaLink, FaCube,  FaBraille, FaExclamationTriangle, FaCog, FaSignOutAlt} from "react-icons/fa";

const TheSidebar = ({ showSidebar }) => {
  return (
    <div className={`sidebar ${showSidebar ? '' : 'active'}`}>
      <ul>
        <li className="iconBox"></li>
        <a href="#home">
          <li><FaHome style={{color: '#0092FF'}}/> Home</li>
        </a>
        <a href="#linkbutton">
          <li><FaLink style={{color: '#FF92FF'}}/> Link Button</li>
        </a>
        <a href="#bridge">
          <li><FaCube style={{color: '#FF9E00'}}/> Bridge</li>
        </a>
        <a href="#devices">
          <li><FaBraille style={{color: '#764600'}}/> Devices</li>
        </a>
        <a href="#deconz">
          <li><FaCube style={{color: '#42A138'}}/> Deconz</li>
        </a>
        <a href="#MQTT">
          <li><FaCube style={{color: '#0084FF'}}/> MQTT</li>
        </a>
        <a href="#alerts">
          <li><FaExclamationTriangle style={{color: '#AE2D00'}}/> Alerts</li>
        </a>
        <a href="#settings">
          <li><FaCog style={{color: '#8B00FF'}}/> Settings</li>
        </a>
        <a href="#logout">
          <li><FaSignOutAlt style={{color: '#fff'}}/> Logout</li>
        </a>
      </ul>
    </div>
  )
}

export default React.memo(TheSidebar)
