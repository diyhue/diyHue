import React, { useRef, useEffect } from "react";
import { colorTemperatureToRgb } from "../color";
import iro from "@jaames/iro";
import axios from "axios";

export default function KelvinPicker({ HOST_IP, api_key, group, groupId }) {
  const pickerRef = useRef(null);
  const picker = useRef(null);

  useEffect(() => {
    const onChange = (newState) => {
      let kelvin = newState.kelvin;
      let mirek = Math.floor((11000 - kelvin) / 25.5 + 153);
      //console.log("#########");
      //console.log(mirek);
      //console.log(colorTemperatureToRgb(group["action"]["ct"]));
      //console.log("Apply state " + JSON.stringify(newState));
      axios.put(`${HOST_IP}/api/${api_key}/groups/${groupId}/action`, {
        ct: mirek,
      });
    };

    if (pickerRef.current && !picker.current) {
      picker.current = new iro.ColorPicker(pickerRef.current, {
        layoutDirection: "horizontal",
        layout: [
          {
            component: iro.ui.Slider,
            options: {
              sliderType: "kelvin",
              sliderShape: "circle",
            },
          },
        ],
        color: colorTemperatureToRgb(group["action"]["ct"]),
      });
      picker.current.on("input:end", onChange);
    }
  }, [group, groupId, HOST_IP, api_key]);
  return <div ref={pickerRef}></div>;
}
