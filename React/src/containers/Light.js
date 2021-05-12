import { FaLightbulb, FaCheck } from "react-icons/fa";
import { MdDeleteForever, MdSystemUpdate } from "react-icons/md";
import { RiAlertLine } from "react-icons/ri";
import { useState } from "react";
import axios from "axios";
import {cieToRgb, colorTemperatureToRgb } from "../color";
import Dropdown from 'react-dropdown';
import 'react-dropdown/style.css';


const Light = ({api_key, id, light, modelIds, setType, setMessage}) => {

  const deleteLight = () => {
    axios.delete(`/api/${api_key}/lights/${id}`)
    .then((fetchedData) => {
      console.log(fetchedData.data);
      setMessage('Light successfully deleted');
      setType('none');
      setType('success');
    }).catch((error) => {
      console.error(error)
      setMessage('Error occured, check browser console');
      setType('none');
      setType('error');
    });
  }

  const alertLight = () => {
    axios.put(`/api/${api_key}/lights/${id}/state`, {"alert": "select"})
    .then((fetchedData) => {
      console.log(fetchedData.data);
      setMessage('Light alerted');
      setType('none');
      setType('success');
    }).catch((error) => {
      console.error(error)
      setMessage('Error occured, check browser console');
      setType('none');
      setType('error');
    });
  }

  const setModelId = (modelid) => {
    console.log( {[id]: modelid})
    axios.post(`/light-types`, {[id]: modelid})
    .then((fetchedData) => {
      console.log(fetchedData.data);
      setMessage('Modelid updated');
      setType('none');
      setType('success');
    }).catch((error) => {
      console.error(error)
      setMessage('Error occured, check browser console');
      setType('none');
      setType('error');
    });
  }

  return (
    <>
    <div className="iconContainer">
      <FaLightbulb onClick={() => alertLight()}/>
    </div>
    {light["name"]} {light['state']['reachable'] && <FaCheck title='Reachable'/> || <RiAlertLine title='Unrechable'/>}<br/>
    <Dropdown options={modelIds} value={light["modelid"]} onChange={(e) => setModelId(e.value)} placeholder="Choose light modelid" />
     Protocol: {light["protocol"]}<br/> IP: {light["protocol_cfg"]["ip"]}<br/>
    <MdDeleteForever title='Delete' onClick={() => deleteLight()}/>  <MdSystemUpdate title='Update' />
    </>
  )
}

export default Light
