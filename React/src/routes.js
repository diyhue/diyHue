import React from 'react';

const Groups = React.lazy(() => import('./views/Groups'));
const LinkButton = React.lazy(() => import('./views/LinkButton'));
const Mqtt = React.lazy(() => import('./views/Mqtt'));
const Deconz = React.lazy(() => import('./views/Deconz'));
const Alarm = React.lazy(() => import('./views/Alarm'));

const routes = [
  { path: '/', exact: true, name: 'Lights', component: Groups },
  { path: '/groups', exact: true, name: 'Groups', component: Groups },
  { path: '/linkbutton', exact: true, name: 'LinkButton', component: LinkButton },
  { path: '/mqtt', exact: true, name: 'MQTT', component: Mqtt },
  { path: '/deconz', exact: true, name: 'Deconz', component: Deconz },
  { path: '/alarm', exact: true, name: 'Alarm', component: Alarm },
  //{ path: '/lights', name: 'Lights', component: Light }
];

export default routes;
