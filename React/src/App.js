import React, { useState, Component } from "react";
import { HashRouter, Route, Switch } from 'react-router-dom';
import './scss/style.scss';


const loading = (
  <div className="pt-3 text-center">
    <div className="sk-spinner sk-spinner-pulse"></div>
  </div>
)

// Containers
//const TheLayout = React.lazy(() => import('./containers/TheLayout'));

// Pages
//const Login = React.lazy(() => import('./views/Login'));
//const Page404 = React.lazy(() => import('./views/Page404'));
//const Page500 = React.lazy(() => import('./views/Page500'));
const Lights = React.lazy(() => import('./views/Lights'));


class App extends Component {

  render() {
    return (
      <HashRouter>
          <React.Suspense fallback={loading}>
            <Switch>
              <Route exact path="/login" name="Login Page" render={props => <Lights {...props}/>} />
              <Route exact path="/404" name="Page 404" render={props => <Lights {...props}/>} />
              <Route exact path="/500" name="Page 500" render={props => <Lights {...props}/>} />
              <Route path="/" name="Home" render={props => <Lights {...props}/>} />
            </Switch>
          </React.Suspense>
      </HashRouter>
    );
  }
}

export default App;
