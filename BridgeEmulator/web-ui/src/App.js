import React from "react";
import styled, { css } from "react-emotion";
import AppBar from "@material-ui/core/AppBar";
import Toolbar from "@material-ui/core/Toolbar";
import Typography from "@material-ui/core/Typography";
import Switch from "@material-ui/core/Switch";
import Room from "./Room";

const Root = styled("div")`
  flex-grow: 1;
`;

const flex = css`
  flex: 1;
`;

const anyLightOn = groups =>
  Object.values(groups).some(group => group.state.any_on);

export default ({
  groups,
  lights,
  onColorTemperatureChange,
  onColorChange,
  onBrightnessChange,
  onStateChange,
  onGlobalStateChange
}) => (
  <Root>
    <AppBar position="static">
      <Toolbar>
        <Typography variant="title" color="inherit" className={flex}>
          Hue Emulator
        </Typography>
        <Switch
          checked={anyLightOn(groups)}
          onChange={() => onGlobalStateChange(!anyLightOn(groups))}
        />Turn all {anyLightOn(groups) ? "off" : "on"}
      </Toolbar>
    </AppBar>
    {Object.keys(groups)
      .map(id => ({ ...groups[id], id }))
      .map(group => (
        <Room
          key={group.id}
          room={group}
          lights={lights}
          setColorTemperature={onColorTemperatureChange}
          setColor={onColorChange}
          setBrightness={onBrightnessChange}
          setState={onStateChange}
        />
      ))}
  </Root>
);
