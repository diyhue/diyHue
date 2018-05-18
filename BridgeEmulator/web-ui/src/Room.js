import React, { Fragment } from "react";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemIcon from "@material-ui/core/ListItemIcon";
import ListItemSecondaryAction from "@material-ui/core/ListItemSecondaryAction";
import ListItemText from "@material-ui/core/ListItemText";
import ListSubheader from "@material-ui/core/ListSubheader";
import MdiIconButton from "@material-ui/core/IconButton";
import LightbulbOnIcon from "mdi-react/LightbulbOnIcon";
import LightbulbOutlineIcon from "mdi-react/LightbulbOutlineIcon";
import Switch from "@material-ui/core/Switch";
import Dialog from "@material-ui/core/Dialog";
import DialogActions from "@material-ui/core/DialogActions";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Button from "@material-ui/core/Button";
import Avatar from "@material-ui/core/Avatar";
import BrightnessIcon from "mdi-react/Brightness6Icon";
import TemperatureKelvinIcon from "mdi-react/TemperatureKelvinIcon";
import PaletteIcon from "mdi-react/PaletteIcon";
import styled from "react-emotion";
import { HuePicker } from "react-color";

// TODO: style this slider to match Material Design
import Slider from "rc-slider";
import "rc-slider/assets/index.css";
import { compose, withState, lifecycle } from "recompose";
import _throttle from "lodash/fp/throttle";
import color from "./color";
import { cieToRgb } from "./color";
import { colorTemperatureToRgb } from "./color";

const TemperatureSlider = styled(Slider)`
  .rc-slider-rail {
    background-image: linear-gradient(
      to right,
      #5373d8,
      #c7e1fd,
      #fae3a8,
      #c14334
    );
  }
  .rc-slider-track {
    background: transparent;
  }
`;

const StyledList = styled(List)`
  width: 500px;
  max-width: calc(100vw - 80px);
`;

const IconButton = styled(MdiIconButton)`
  margin-top: -0.5em !important;
  margin-bottom: -0.5em !important;
`;

const enhance = compose(
  withState("isDialogOpen", "setDialogOpen", false),
  withState("selectedLight", "setSelectedLight", undefined),
  withState(
    "smallScreen",
    "setSmallScreen",
    window.matchMedia("(max-width: 800px)").matches
  ),
  lifecycle({
    componentDidMount() {
      window.addEventListener(
        "resize",
        _throttle(500)(() =>
          this.props.setSmallScreen(
            window.matchMedia("(max-width: 800px)").matches
          )
        )
      );
    }
  })
);

const Room = ({
  setColorTemperature,
  setColor,
  setBrightness,
  setState,
  room,
  lights,
  isDialogOpen,
  setDialogOpen,
  selectedLight,
  setSelectedLight,
  smallScreen
}) => (
  <List
    subheader={
      <ListSubheader>
        {room.name}
        <ListItemSecondaryAction>
          <Switch
            checked={room.state.any_on}
            onChange={() => setState(room, !room.state.any_on)}
          />
        </ListItemSecondaryAction>
      </ListSubheader>
    }
  >
    {room.lights
      .filter(id => Boolean(lights[id]))
      .map(id => ({ ...lights[id], id }))
      .map(light => (
        <ListItem key={light.id}>
          <ListItemIcon>
            <IconButton
              onClick={() => {
                setDialogOpen(true);
                setSelectedLight(light);
              }}
            >
              {light.state.on ? (
                <LightbulbOnIcon
                  color={
                    light.state.colormode === "ct"
                      ? colorTemperatureToRgb(light.state.ct)
                      : light.state.colormode === "xy"
                      ? cieToRgb(
                          light.state.xy[0],
                          light.state.xy[1],
                          light.state.bri
                        )
                      : '#fcf794'
                  }
                />
              ) : (
                <LightbulbOutlineIcon />
              )}
            </IconButton>
          </ListItemIcon>
          <ListItemText primary={light.name} />
          <ListItemSecondaryAction>
            <Switch
              checked={light.state.on}
              onChange={() => setState(light, !light.state.on)}
            />
          </ListItemSecondaryAction>
        </ListItem>
      ))}
    <Dialog
      fullScreen={smallScreen}
      open={isDialogOpen}
      onClose={() => setDialogOpen(false)}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
    >
      {selectedLight ? (
        <Fragment>
          <DialogTitle id="alert-dialog-title">
            {room.name} {selectedLight.name}
          </DialogTitle>
          <DialogContent>
            <StyledList>
              {"bri" in selectedLight.state && (
                <ListItem>
                  <Avatar>
                    <BrightnessIcon color="white" />
                  </Avatar>
                  <ListItemText
                    primary={
                      <Slider
                        min={0}
                        max={255}
                        defaultValue={
                          selectedLight.state.on ? selectedLight.state.bri : 0
                        }
                        onChange={bri => setBrightness(selectedLight, bri)}
                      />
                    }
                    secondary="Brghtness"
                  />
                </ListItem>
              )}
              {"ct" in selectedLight.state && (
                <ListItem>
                  <Avatar>
                    <TemperatureKelvinIcon color="white" />
                  </Avatar>
                  <ListItemText
                    primary={
                      <TemperatureSlider
                        min={153}
                        max={500}
                        defaultValue={Math.max(
                          153,
                          Math.min(selectedLight.state.ct, 500)
                        )}
                        onChange={temp =>
                          setColorTemperature(selectedLight, temp)
                        }
                      />
                    }
                    secondary="Temperature"
                  />
                </ListItem>
              )}
              {("xy" in selectedLight.state ||
                "hue" in selectedLight.state) && (
                <ListItem>
                  <Avatar>
                    <PaletteIcon color="white" />
                  </Avatar>
                  <ListItemText
                    primary={
                      <HuePicker
                        width="100%"
                        color={cieToRgb(selectedLight.state.xy[0],selectedLight.state.xy[1],selectedLight.state.bri)}
                        defaultColor={color[selectedLight.state.colormode](
                          selectedLight
                        )}
                        onChange={color => setColor(selectedLight, color)}
                      />
                    }
                    secondary="Color"
                  />
                </ListItem>
              )}
            </StyledList>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => setDialogOpen(false)}
              color="primary"
              autoFocus
            >
              Close
            </Button>
          </DialogActions>
        </Fragment>
      ) : (
        <span />
      )}
    </Dialog>
  </List>
);

export default enhance(Room);
