import { useState, useEffect } from 'react'
import axios from "axios";
import Flash from "../containers/Flash"

const Deconz = ({ API_KEY }) => {
  const [type, setType] = useState('none');
  const [message, setMessage] = useState('no message');
  const [enable, setEnable] = useState(false)
  const [deconzHost, setDeconzHost] = useState('127.0.0.1')
  const [deconzPort, setDeconzPort] = useState(8443)

  useEffect(() => {
    axios.get(`/api/${API_KEY}/config/deconz`).then((result) => {
        setEnable(result.data["enabled"]);
        setDeconzHost(result.data["deconzHost"]);
        setDeconzPort(result.data["deconzPort"]);
    }).catch((error) => {console.error(error)});
  }, []);

  const onSubmit = (e) => {
    console.log("submit")
    e.preventDefault()
    axios
      .put(
        `/api/${API_KEY}/config`,
        {'deconz': {'enabled': enable, 'deconzHost': deconzHost, 'deconzPort': deconzPort}}
      ).then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage('Successfully saved, please restart the service');
        setType('success');
      }).catch((error) => {
        console.error(error)
        setMessage('Error occured, check browser console');
        setType('error');
      });
  }

  return (
    <div className="content">
        {type !== 'none' && <Flash type={type} message={message} duration="5000" setType={setType} />}
        <div className='contentContainer'>
          <form className='add-form' onSubmit={onSubmit}>
          <div className="switchContainer">
          <label className="switch">
            <input type="checkbox"
              value={enable}
              checked={enable}
              onChange={(e) => setEnable(e.target.checked)}
            />
            <span className="slider"></span>
          </label>
        </div>
          <div className='form-control'>
              <label>Deconz host</label>
              <input
              type='text'
              placeholder='Deconz host'
              value={deconzHost}
              onChange={(e) => setDeconzHost(e.target.value)}
              />
          </div>
          <div className='form-control'>
              <label>Deconz port</label>
              <input
              type='number'
              placeholder='Deconz port'
              value={deconzPort}
              onChange={(e) => setDeconzPort(e.target.value)}
              />
          </div>
          <div className='form-control'>
            <input type='submit' value='Save' className='btn btn-block green' />
          </div>
          </form>
        </div>
    </div>
  )
}

export default Deconz