import { useState } from "react";

import {
  TheContent,
  TheSidebar,
  TheHeader
} from './index'

const TheLayout = () => {

  const [showSidebar, setShowSidebar] = useState(true);

  return (
    <>
      <TheHeader
        showSidebar = {showSidebar}
        setShowSidebar = {setShowSidebar}
      />
      <TheSidebar
        showSidebar = {showSidebar}
      />
      <TheContent/>
      </>
  )
}

export default TheLayout
