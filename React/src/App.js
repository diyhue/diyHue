import React, { useState } from "react";
import "./App.css";
import Lights from "./Lights";
import LinkButton from "./LinkButton";

export default function App() {
  const [showLinkButtonPage, setShowLinkButtonPage] = useState(false);

  return (
    <div className="App">
      <nav>
        <ul>
          <li>
            <a href="/lighst">Lights</a>
          </li>
          <li>
            <a href="/linkbutton">Link Button</a>
          </li>
        </ul>
      </nav>
      {!showLinkButtonPage ? <Lights /> : <LinkButton />}
    </div>
  );
}
