import React from 'react'
import TheLayout from './containers/TheLayout'

import './scss/style.scss';
//import "./App.css";

const loading = (
  <div className="pt-3 text-center">
    <div className="sk-spinner sk-spinner-pulse"></div>
  </div>
)
/* Your tree is:

- App
    - TheLayout
        - TheHeader
        - TheSidebar
        - The Content
            - Route depending on routes.js
                - E.g. Groups
                - E.g. LinkButton

If you fetch the API in groups you need me make sure where you need the result
If you need it in another component on the same level, you need it at least one level higher and pass it down
There are basically two different ways on passing data around;

  1. Fetch it on App.js level and pass it all the way down.
  2. use a context - load it at e.g. app level and consume it directly there, where you need it - level doesn't matter


  useEffect(() => {
    axios
      .get("/api/local")
      .then((fetchedData) => {
        setConfig(fetchedData.data);
      });
  }, [groupState]); <------ This peformes a fetch the first time the group components gets rendered and every time, the groupState changes.
  If you have that on the App level, every components gets rerendered, that consumes that value.

*/

const App = () => {

  return (
      <React.Suspense fallback={loading}>
        <div className="flexContainer">
          <TheLayout/>
        </div>
      </React.Suspense>
  )
}

export default App
