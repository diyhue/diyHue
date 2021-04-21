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
      <p>Description for Linkbutton</p>
      <div className="linkbtn" onClick={() => pushLinkButton()}>Call to action
      </div>
    </div>
  );
}
