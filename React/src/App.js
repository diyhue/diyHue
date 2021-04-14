import React from 'react'
import TheLayout from './containers/TheLayout'

import './scss/style.scss';
//import "./App.css";

const loading = (
  <div className="pt-3 text-center">
    <div className="sk-spinner sk-spinner-pulse"></div>
  </div>
)

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
