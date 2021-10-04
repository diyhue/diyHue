import React, { useRef, useEffect, useState } from "react";
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

  let colors = [];
  for (const [index, light] of groupLights.entries()) {
    console.log(light);
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
  const onChange = (newState) => {
    let rgb = newState.rgb;

    console.log(newState.rgb);
    console.log("Apply state " + JSON.stringify(newState));
    axios.put(
      `${HOST_IP}/api/${api_key}/lights/${groupLights[newState["index"]]
      }/state`,
      { xy: rgbToCie(rgb["r"], rgb["g"], rgb["b"]) }
    );
  };

  useEffect(() => {
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
  }, [onChange]);
  return <div ref={pickerRef}></div>;
}
