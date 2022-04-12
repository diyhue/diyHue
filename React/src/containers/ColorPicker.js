import React, { useRef, useEffect } from "react";
import { cieToRgb, rgbToCie } from "../color";
import iro from "@jaames/iro";
import axios from "axios";

export default function KelvinPicker({
  HOST_IP,
  api_key,
  lights,
  groupLights,
}) {
  const pickerRef = useRef(null);
  const picker = useRef(null);

  useEffect(() => {
    const onChange = (newState) => {
      let rgb = newState.rgb;

      //console.log(newState.rgb);
      //console.log("Apply state " + JSON.stringify(newState));
      axios.put(
        `${HOST_IP}/api/${api_key}/lights/${
          groupLights[newState["index"]]
        }/state`,
        { xy: rgbToCie(rgb["r"], rgb["g"], rgb["b"]) }
      );
    };

    let colors = [];
    for (var light of groupLights.entries()) {
      light = light[1];
      if ("xy" in lights[light]["state"]) {
        colors.push(
          cieToRgb(
            lights[light]["state"]["xy"][0],
            lights[light]["state"]["xy"][1],
            254
          )
        );
      }
    }

    if (pickerRef.current && !picker.current) {
      picker.current = new iro.ColorPicker(pickerRef.current, {
        layout: [
          {
            component: iro.ui.Wheel,
            options: {},
          },
        ],
        colors: colors,
      });
      //console.log(picker.current.state.color.rgb)
      picker.current.on("input:end", onChange);
    }
  }, [groupLights, lights, HOST_IP, api_key]);
  return <div ref={pickerRef}></div>;
}
