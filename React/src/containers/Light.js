import { FaLightbulb } from "react-icons/fa";
import { useState } from "react";
import axios from "axios";
import {cieToRgb, colorTemperatureToRgb } from "../color";

const Light = ({api_key, id, light}) => {

  return (
    <> 
    <div className="iconContainer">
            <FaLightbulb/>
          </div>
    {light["name"]} {light["modelid"]}  {light["protocol"]} <br/>
    </>
  )
}

export default Light
