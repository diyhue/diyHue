import React from "react";
import { css } from "react-emotion";
import { withStyles } from "@material-ui/core/styles";
import AppBar from "@material-ui/core/AppBar";
import Toolbar from "@material-ui/core/Toolbar";
import Typography from "@material-ui/core/Typography";
import Switch from "@material-ui/core/Switch";
import Drawer from "@material-ui/core/Drawer";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemIcon from "@material-ui/core/ListItemIcon";
import ListItemText from "@material-ui/core/ListItemText";
import IconButton from "@material-ui/core/IconButton";
import Hidden from "@material-ui/core/Hidden";
import LightbulbOnIcon from "mdi-react/LightbulbOnIcon";
import LinkIcon from "mdi-react/LinkVariantIcon";
import ImportIcon from "mdi-react/ImportIcon";
import MenuIcon from "mdi-react/MenuIcon";
import { State } from "react-powerplug";
import Room from "./Room";

const flex = css`
  flex: 1;
`;

const drawerWidth = 240;

const styles = theme => ({
  root: {
    flexGrow: 1,
    height: "100vh",
    zIndex: 1,
    overflow: "hidden",
    position: "relative",
    display: "flex"
  },
  appBar: {
    zIndex: theme.zIndex.drawer + 1,
    marginLeft: drawerWidth,
    [theme.breakpoints.up("md")]: {
      width: `calc(100% - ${drawerWidth}px)`
    }
  },
  navIconHide: {
    [theme.breakpoints.up("md")]: {
      display: "none"
    }
  },
  toolbar: theme.mixins.toolbar,
  drawerPaper: {
    width: drawerWidth,
    [theme.breakpoints.up("md")]: {
      position: "relative"
    }
  },
  content: {
    flexGrow: 1,
    overflow: "auto",
    backgroundColor: theme.palette.background.default,
    padding: theme.spacing.unit * 3,
    minWidth: 0 // So the Typography noWrap works
  }
});

const anyLightOn = groups =>
  Object.values(groups).some(group => group.state.any_on);

const navigation = (
  <List component="nav">
    <ListItem button href="/" component="a">
      <ListItemIcon>
        <LightbulbOnIcon />
      </ListItemIcon>
      <ListItemText>Lights control</ListItemText>
    </ListItem>

    <ListItem button href="/hue" component="a">
      <ListItemIcon>
        <ImportIcon />
      </ListItemIcon>
      <ListItemText>Import from bridge</ListItemText>
    </ListItem>

    <ListItem button href="/hue/linkbutton" component="a">
      <ListItemIcon>
        <LinkIcon />
      </ListItemIcon>
      <ListItemText>Link device</ListItemText>
    </ListItem>
  </List>
);

const App = ({
  classes,
  groups,
  lights,
  onColorTemperatureChange,
  onColorChange,
  onBrightnessChange,
  onStateChange,
  onGlobalStateChange
}) => (
  <State initial={{ drawer: false }}>
    {({ state, setState }) => (
      <div className={classes.root}>
        <AppBar position="absolute" className={classes.appBar}>
          <Toolbar>
            <IconButton
              onClick={() => setState({ drawer: true })}
              className={classes.navIconHide}
            >
              <MenuIcon color="white" />
            </IconButton>
            <Typography variant="title" color="inherit" className={flex}>
              Hue Emulator
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={anyLightOn(groups)}
                  onChange={() => onGlobalStateChange(!anyLightOn(groups))}
                />
              }
              label={
                <span style={{ color: "white" }}>
                  Turn all {anyLightOn(groups) ? "off" : "on"}
                </span>
              }
            />
          </Toolbar>
        </AppBar>
        <Hidden mdUp>
          <Drawer
            variant="temporary"
            open={state.drawer}
            onClose={() => setState({ drawer: false })}
            classes={{
              paper: classes.drawerPaper
            }}
            ModalProps={{
              keepMounted: true // Better open performance on mobile.
            }}
          >
            <div className={classes.toolbar} />
            {navigation}
          </Drawer>
        </Hidden>
        <Hidden smDown implementation="css">
          <Drawer
            variant="permanent"
            open
            onClose={() => setState({ drawer: false })}
            classes={{
              paper: classes.drawerPaper
            }}
          >
            <div className={classes.toolbar} />
            {navigation}
          </Drawer>
        </Hidden>
        <main className={classes.content}>
          <div className={classes.toolbar} />
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
        </main>
      </div>
    )}
  </State>
);

export default withStyles(styles)(App);
