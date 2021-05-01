import { useState, useEffect } from 'react'
import axios from "axios";
import Flash from "../containers/Flash"

const Alarm = ({ API_KEY }) => {
  const [type, setType] = useState('none');
  const [message, setMessage] = useState('no message');
  const [enable, setEnable] = useState(false)
  const [email, setEmail] = useState('none')

  useEffect(() => {
    axios.get(`/api/${API_KEY}/config/alarm`).then((result) => {
        setEnable(result.data["enabled"]);
        setEmail(result.data["email"]);
    }).catch((error) => {console.error(error)});
  }, []);

  const onSubmit = (e) => {
    console.log("submit")
    e.preventDefault()
    axios
      .put(
        `/api/${API_KEY}/config`,
        {'alarm': {'enabled': enable, 'email': email}}
      ).then((fetchedData) => {
        console.log(fetchedData.data);
        setMessage('Successfully saved');
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
            <label>e-mail</label>
            <input
            type='text'
            placeholder='Notification email'
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            />
        </div>
        <input type='submit' value='Save' className='btn btn-block' />
        </form>
    </div>
  )
}

export default Alarm