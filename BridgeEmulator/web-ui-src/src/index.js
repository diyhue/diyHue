import React from "react";
import { render } from "react-dom";
import { injectGlobal } from "react-emotion";
import { compose, withState, lifecycle, withProps } from "recompose";
import _throttle from "lodash/fp/throttle";
import App from "./App";
import { rgbToCie } from "./color";

injectGlobal`
  html, body {
    margin: 0;
  }
`;

export function httpPutRequest(url, data) {
  return fetch(url, {
    method: "PUT",
    mode: "cors",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then(res => {
      return res;
    })
    .catch(err => console.error(err.message));
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
    onColorTemperatureChange: throttle((entity, temp) =>
      httpPutRequest(`/api/${API_KEY}/lights/${entity.id}/state`, { ct: temp })
    ),
    onColorChange: throttle((entity, color) =>
      httpPutRequest(`/api/${API_KEY}/lights/${entity.id}/state`, {
        xy: rgbToCie(color["rgb"]["r"], color["rgb"]["g"], color["rgb"]["b"])
      })
    ),
    onBrightnessChange: throttle((entity, bri) =>
      httpPutRequest(`/api/${API_KEY}/lights/${entity.id}/state`, { bri: bri })
    ),
    onStateChange: (entity, state) =>
      httpPutRequest(
        `/api/${API_KEY}/${
          entity.type === "Room"
            ? "groups/" + entity.id + "/action"
            : "lights/" + entity.id + "/state"
        }`,
        { on: state }
      ),
    // this should trigger a state change on ALL the available lights
    onGlobalStateChange: state =>
      httpPutRequest(`/api/${API_KEY}/groups/0/action`, { on: state })
  }),
  lifecycle({
    async componentDidMount() {
      setInterval(async () => {
        const res = await Promise.all([
          fetch(`/api/${API_KEY}/groups`),
          fetch(`/api/${API_KEY}/lights`)
        ]);
        const json = await Promise.all([res[0].json(), res[1].json()]);

        this.props.setGroups(json[0]);
        this.props.setLights(json[1]);
      }, 1000);
    }
  })
);

const AppWithData = enhance(App);

render(<AppWithData />, document.getElementById("root"));
