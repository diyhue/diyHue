import { useState, useEffect } from 'react'
import axios from "axios";
import Flash from "../containers/Flash"

const Mqtt = ({ API_KEY }) => {
  const [type, setType] = useState('none');
  const [message, setMessage] = useState('no message');
  const [enable, setEnable] = useState(false)
  const [mqttServer, setMqttServer] = useState('mqtt')
  const [mqttPort, setMqttPort] = useState(1883)
  const [mqttUser, setMqttUser] = useState('')
  const [mqttPass, setMqttPass] = useState('')

  useEffect(() => {
    axios.get(`/api/${API_KEY}/config/mqtt`).then((result) => {
      setEnable(result.data["enabled"]);
      setMqttServer(result.data["mqttServer"]);
      setMqttPort(result.data["mqttPort"]);
      setMqttUser(result.data["mqttUser"]);
      setMqttPass(result.data["mqttPassword"]);
    }).catch((error) => { console.error(error) });
  }, []);

  const onSubmit = (e) => {
    console.log("submit")
    e.preventDefault()
    axios
      .put(
        `/api/${API_KEY}/config`,
        { 'mqtt': { 'enabled': enable, 'mqttServer': mqttServer, 'mqttPort': mqttPort, 'mqttUser': mqttUser, 'mqttPassword': mqttPass } }
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
            <label>MQTT server</label>
            <input
              type='text'
              placeholder='MQTT server'
              value={mqttServer}
              onChange={(e) => setMqttServer(e.target.value)}
            />
          </div>
          <div className='form-control'>
            <label>MQTT port</label>
            <input
              type='number'
              placeholder='MQTT port'
              value={mqttPort}
              onChange={(e) => setMqttPort(parseInt(e.target.value))}
            />
          </div>
          <div className='form-control'>
            <label>MQTT username</label>
            <input
              type='text'
              placeholder='MQTT username'
              value={mqttUser}
              onChange={(e) => setMqttUser(e.target.value)}
            />
          </div>
          <div className='form-control'>
            <label>MQTT password</label>
            <input
              type='text'
              placeholder='MQTT password'
              value={mqttPass}
              onChange={(e) => setMqttPass(e.target.value)}
            />
          </div>
          <div className='form-control'>
            <input type='submit' value='Save' className='btn btn-block' />
          </div>
        </form>
      </div>
    </div>
  )
}

export default Mqtt