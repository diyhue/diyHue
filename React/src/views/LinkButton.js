import axios from "axios";

export default function LinkButton({API_KEY}) {
  console.log(API_KEY)

  const pushLinkButton = () => {
    axios
      .put(
        `/api/${API_KEY}/config`,
        {'linkbutton': {'lastlinkbuttonpushed': Date.now()}}
      )
    };

  return (
    <div className="content">
      <div className="contentContainer">
        <p>Push this button to accept the pairing of the requested app</p>
        <div className="linkbtn" onClick={() => pushLinkButton()}>Link App
        <div class="linkbtn2"></div></div>
      </div>
    </div>
  );
}
