import { useState } from "react";
import { useMediaQuery } from "react-responsive";
import { TheContent, TheSidebar, TheHeader } from "./index";

const TheLayout = ({ HOST_IP, API_KEY }) => {
  const isMobile = useMediaQuery({ query: `(max-width: 760px)` });
  const [showSidebar, setShowSidebar] = useState(!isMobile);

  return (
    <>
      <TheHeader
        HOST_IP={HOST_IP}
        API_KEY={API_KEY}
        showSidebar={showSidebar}
        setShowSidebar={setShowSidebar}
      />
      <TheSidebar showSidebar={showSidebar} />
      <TheContent HOST_IP={HOST_IP} API_KEY={API_KEY} />
    </>
  );
};

export default TheLayout;
