import React from "react";
import { render } from "react-dom";
import { injectGlobal } from "react-emotion";
import { compose, withState, lifecycle, withProps } from "recompose";
import _throttle from "lodash/fp/throttle";
import App from "./App";

injectGlobal`
  html, body {
    margin: 0;
  }
`;

export function httpPutRequest(url, data) {
    return fetch(url, {
        method: 'PUT',
        mode: 'CORS',
        body: JSON.stringify(data),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(res => {
        return res;
    }).catch(err => console.error(err.message));
}

export function rgbToCie(red, green, blue) {
  //Apply a gamma correction to the RGB values, which makes the color more vivid and more the like the color displayed on the screen of your device
  var red =
    red > 0.04045 ? Math.pow((red + 0.055) / (1.0 + 0.055), 2.4) : red / 12.92;
  var green =
    green > 0.04045
      ? Math.pow((green + 0.055) / (1.0 + 0.055), 2.4)
      : green / 12.92;
  var blue =
    blue > 0.04045
      ? Math.pow((blue + 0.055) / (1.0 + 0.055), 2.4)
      : blue / 12.92;

  //RGB values to XYZ using the Wide RGB D65 conversion formula
  var X = red * 0.664511 + green * 0.154324 + blue * 0.162028;
  var Y = red * 0.283881 + green * 0.668433 + blue * 0.047685;
  var Z = red * 0.000088 + green * 0.07231 + blue * 0.986039;

  //Calculate the xy values from the XYZ values
  var x = (X / (X + Y + Z)).toFixed(4);
  var y = (Y / (X + Y + Z)).toFixed(4);

  if (isNaN(x)) x = 0;

  if (isNaN(y)) y = 0;

  return [parseFloat(x), parseFloat(y)];
}

const API_KEY = window.config.API_KEY;
const THROTTLE_WAIT = 1000; // 1 second

const throttle = _throttle(THROTTLE_WAIT);

const enhance = compose(
  withState("groups", "setGroups", {}),
  withState("lights", "setLights", {}),
  // TODO: change these methods to hook the Hue Emulator API calls
  // entity may be a light or a room, they have an extra `id` property
  // the second argument is the new value selected by the user
  withProps({
    onColorTemperatureChange: throttle((entity, temp) => httpPutRequest(`/api/${API_KEY}/lights/${entity.id}/state`,{"ct": temp})),
    onColorChange: throttle((entity, color) => httpPutRequest(`/api/${API_KEY}/lights/${entity.id}/state`,{"xy": rgbToCie(color['rgb']['r'], color['rgb']['g'], color['rgb']['b'])})),
    onBrightnessChange: throttle((entity, bri) => httpPutRequest(`/api/${API_KEY}/lights/${entity.id}/state`,{"bri": bri})),
    onStateChange: (entity, state) => httpPutRequest(`/api/${API_KEY}/${entity.type === "Room" ? "groups/"+ entity.id + "/action":"lights/" + entity.id + "/state"}`,{"on": state}),
    // this should trigger a state change on ALL the available lights
    onGlobalStateChange: (state) => httpPutRequest(`/api/${API_KEY}/groups/0/action`,{"on": state})
  }),
  lifecycle({
    async componentDidMount() {
      const res = await Promise.all([
        fetch(`/api/${API_KEY}/groups`),
        fetch(`/api/${API_KEY}/lights`)
      ]);
      const json = await Promise.all([res[0].json(), res[1].json()]);

      this.props.setGroups(json[0]);
      this.props.setLights(json[1]);
    }
  })
);

const AppWithData = enhance(App);

render(<AppWithData />, document.getElementById("root"));
