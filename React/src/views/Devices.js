import { useState, useEffect } from 'react'
import axios from "axios";
import Flash from "../containers/Flash"

const Devices = ({ API_KEY }) => {
  const [type, setType] = useState('none');
  const [message, setMessage] = useState('no message');



  return (
    <div className="content">
      {type !== 'none' && <Flash type={type} message={message} duration="5000" setType={setType} />}
      <p> Work in progress</p>
    </div>
  )
}

export default Devices