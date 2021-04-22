import { useState } from "react";

import {
  TheContent,
  TheSidebar,
  TheHeader
} from './index'

const TheLayout = ({API_KEY}) => {

  const [showSidebar, setShowSidebar] = useState(true);

  return (
    <>
      <TheHeader
        API_KEY = {API_KEY}
        showSidebar = {showSidebar}
        setShowSidebar = {setShowSidebar}
      />
      <TheSidebar
        showSidebar = {showSidebar}
      />
      <TheContent
        API_KEY = {API_KEY}
      />
      </>
  )
}

export default TheLayout
