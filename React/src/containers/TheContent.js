import React, { Suspense } from "react";
import { Redirect, Route, Switch, HashRouter } from "react-router-dom";
import { CFade } from "@coreui/react";

// routes config
import routes from "../routes";

const loading = (
  <div className="pt-3 text-center">
    <div className="sk-spinner sk-spinner-pulse"></div>
  </div>
);

const TheContent = ({ HOST_IP, API_KEY }) => {
  return (
    <div className="content">
      <Suspense fallback={loading}>
        <HashRouter>
          <Switch>
            {routes.map((route, idx) => {
              return (
                route.component && (
                  <Route
                    key={idx}
                    path={route.path}
                    exact={route.exact}
                    name={route.name}
                    render={(props) => (
                      <CFade>
                        <route.component API_KEY={API_KEY} HOST_IP={HOST_IP} />
                      </CFade>
                    )}
                  />
                )
              );
            })}
            <Redirect from="/" to="/groups" />
          </Switch>
        </HashRouter>
      </Suspense>
    </div>
  );
};

export default React.memo(TheContent);
