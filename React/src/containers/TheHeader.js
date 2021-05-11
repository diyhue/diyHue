import { useState, useEffect } from "react";
import { FaBars } from "react-icons/fa";
import axios from "axios";
import logo from '../static/images/logo.svg';
import Flash from './Flash'

const TheHeader = ({showSidebar, setShowSidebar, API_KEY}) => {

  const [group0State, setGroup0State] = useState(false);
  const [type, setType] = useState('none');
  const [message, setMessage] = useState('no message');

  useEffect(() => {
    fetchGroups();
    const interval = setInterval(() => {
      fetchGroups();
    }, 5000); // <<-- ⏱ 1000ms = 1s
    return () => clearInterval(interval);
  }, [API_KEY]);

  const fetchGroups = () => {
    if (API_KEY !== undefined ) {
      axios
      .get(`/api/${API_KEY}/groups/0`)
      .then((fetchedData) => {
        console.log(fetchedData.data);
        setGroup0State(fetchedData.data["state"]["any_on"]);
      }).catch((error) => {console.error(error)});
    }
  }

  const pushLinkButton = () => {
    axios
      .put(
        `/api/${API_KEY}/config`,
        {'linkbutton': {'lastlinkbuttonpushed': Date.now() / 1000 | 0 }}
      ).then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage('Pairing is allowed for 30 seconds');
        setType('none');
        setType('success');
      }).catch((error) => {
        console.error(error)
        setMessage('Error occured, check browser console');
        setType('none');
        setType('error');
      });
    };

  const handleToggleChange = (state) => {
    const newState = {'on': state};
    setGroup0State(state);
    console.log('Apply state ' + JSON.stringify(newState));
    axios.put(`/api/${API_KEY}/groups/0/action`, newState);
  }

  return (
    <div className="topbar">
      <img src={logo} alt="diyHue Logo" />
      <button type="button" id="sidebarCollapse" className="sidebarToggle" onClick={() => setShowSidebar(!showSidebar)}>
        <FaBars/>
        <span></span>
      </button>
      <div className="switchContainer">
        {type !== 'none' && <Flash type={type} message={message} duration="5000" setType={setType} />}
        <button className="headerlinkbtn" onClick={() => pushLinkButton()}>Link App</button>
      </div>
      <div className="switchContainer">
        <p>Turn all {group0State? 'off' : 'on'}</p>
        <label className="switch">
          <input type="checkbox"
            value={group0State}
            checked={group0State}
            onChange={(e) => handleToggleChange(e.target.checked)}
          />
          <span className="slider"></span>
        </label>
      </div>
      <div className="groupToggle"><i onClick="toggleLights(this)" className="fas fa-couch"></i></div>
    </div>
  )
}

export default TheHeader
