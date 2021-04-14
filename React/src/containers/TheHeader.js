import { FaBars } from "react-icons/fa";
import logo from '../static/images/logo.svg';

const TheHeader = ({showSidebar, setShowSidebar}) => {
  return (
    <div className="topbar">
      <img src={logo} alt="diyHue Logo" />
      <button type="button" id="sidebarCollapse" className="sidebarToggle" onClick={() => setShowSidebar(!showSidebar)}>
        <FaBars/>
        <span></span>
      </button>
      <div className="switchContainer">
        <p>Turn all on</p>
        <label className="switch">
          <input type="checkbox"/>
          <span className="slider"></span>
        </label>
      </div>
      <div className="groupToggle"><i onClick="toggleLights(this)" className="fas fa-couch"></i></div>
    </div>
  )
}

export default TheHeader
