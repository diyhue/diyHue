import React from 'react';

const Groups = React.lazy(() => import('./views/Groups'));
const LinkButton = React.lazy(() => import('./views/LinkButton'));

const routes = [
  { path: '/', exact: true, name: 'Lights', component: Groups },
  { path: '/groups', exact: true, name: 'Groups', component: Groups },
  { path: '/linkbutton', exact: true, name: 'LinkButton', component: LinkButton },
  //{ path: '/lights', name: 'Lights', component: Light }
];

export default routes;
