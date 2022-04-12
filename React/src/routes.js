import React from 'react';

const Groups = React.lazy(() => import('./views/Groups'));
const Lights = React.lazy(() => import('./views/Lights'));
const LinkButton = React.lazy(() => import('./views/LinkButton'));
const HA = React.lazy(() => import('./views/HA'));
const Mqtt = React.lazy(() => import('./views/Mqtt'));
const Deconz = React.lazy(() => import('./views/Deconz'));
const Tradfri = React.lazy(() => import('./views/Tradfri'));
const Alarm = React.lazy(() => import('./views/Alarm'));
const Devices = React.lazy(() => import('./views/Devices'));
const Bridge = React.lazy(() => import('./views/Bridge'));
const HueBridge = React.lazy(() => import('./views/HueBridge'));
const About = React.lazy(() => import('./views/About'));
const Settings = React.lazy(() => import('./views/Settings'));

const routes = [
  { path: '/', exact: true, name: 'Groups', component: Groups },
  { path: '/groups', exact: true, name: 'Groups', component: Groups },
  { path: '/lights', exact: true, name: 'Lights', component: Lights },
  { path: '/linkbutton', exact: true, name: 'LinkButton', component: LinkButton },
  { path: '/ha', exact: true, name: 'HA', component: HA },
  { path: '/mqtt', exact: true, name: 'MQTT', component: Mqtt },
  { path: '/deconz', exact: true, name: 'Deconz', component: Deconz },
  { path: '/alarm', exact: true, name: 'Alarm', component: Alarm },
  { path: '/bridge', exact: true, name: 'Bridge', component: Bridge },
  { path: '/devices', exact: true, name: 'Devices', component: Devices },
  { path: '/hue', exact: true, name: 'Hue Bridge', component: HueBridge },
  { path: '/tradfri', exact: true, name: 'Tradfri', component: Tradfri },
  { path: '/about', exact: true, name: 'About', component: About },
  { path: '/settings', exact: true, name: 'Settings', component: Settings },
];

export default routes;
