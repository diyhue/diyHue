import React, { useRef, useEffect, useState } from "react";
import { colorTemperatureToRgb, rgbToCie } from "../color";
import iro from "@jaames/iro";
import axios from "axios";
import { motion } from "framer-motion"

export default function KelvinPicker({
  HOST_IP,
  api_key,
  group,
  groupId
}) {
  const pickerRef = useRef(null);
  const picker = useRef(null);

  const [animation, setAnimation] = useState(true);

  useEffect(() => {
    // Component loads the first time...
    // animation is true => hide class will be returned, so it is opacity 0 (css file at the end)
    // It will be set to false so class *line 54* will be switched
    setAnimation(false);

    //This return function will be fired when the component gets unmounted, so to be sure the color wheel gets faded out
    return () => {
      setAnimation(false);
    };
  }, []);

  const onChange = (newState) => {
    let kelvin = newState.kelvin;
    let mirek = Math.floor((11000 - kelvin) / 25.5 + 153);
    console.log("#########");
    console.log(mirek);
    console.log(colorTemperatureToRgb(group["action"]["ct"]));
    console.log("Apply state " + JSON.stringify(newState));
    axios.put(
      `${HOST_IP}/api/${api_key}/groups/${groupId}/action`,
      { 'ct': mirek }
    );
  };

  useEffect(() => {
    if (pickerRef.current && !picker.current) {
      picker.current = new iro.ColorPicker(pickerRef.current, {
        layout: [
          {
            component: iro.ui.Slider,
            options: {
              sliderType: 'kelvin'
            }
          },
        ],
        color: colorTemperatureToRgb(group["action"]["ct"])
      });
      picker.current.on("input:end", onChange);
    }
  }, [onChange]);
  return <motion.div
    layout
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    ref={pickerRef}>
  </motion.div>;
}
