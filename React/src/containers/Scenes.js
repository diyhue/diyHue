import Modal from "react-modal";
import axios from "axios";
import { FaTimes } from "react-icons/fa";
import { cieToRgb, colorTemperatureToRgb } from "../color";

import nightsky from "../static/images/nightsky.jpg";

const Scenes = ({
  HOST_IP,
  api_key,
  groupId,
  scenes,
  sceneModal,
  setSceneModal,
}) => {
  const applyScene = (scene) => {
    axios.put(`${HOST_IP}/api/${api_key}/groups/0/action`, { scene: scene });
  };

  const applyLightState = (light, state) => {
    axios.put(`${HOST_IP}/api/${api_key}/lights/${light}/state`, state);
  };

  // function openModal() {
  //   setSceneModal(true);
  // }

  function afterOpenModal() {
    // references are now sync'd and can be accessed.
    // subtitle.style.color = '#f00';
  }

  function closeModal() {
    setSceneModal(false);
  }

  const getStyle = (lightstate) => {
    let color;
    if ("xy" in lightstate) {
      color = cieToRgb(lightstate["xy"][0], lightstate["xy"][1], 254);
    } else if ("ct" in lightstate) {
      color = colorTemperatureToRgb(lightstate["ct"]);
    } else {
      color = "rgba(200,200,200,1)";
    }
    return color;
  };

  return (
    <Modal
      isOpen={sceneModal}
      onAfterOpen={afterOpenModal}
      onRequestClose={closeModal}
      contentLabel="Example Modal"
    >
      <div className="header">
        <div className="headline">Scene Picker</div>
        <div className="iconbox">
          <button onClick={closeModal}>
            <FaTimes />
          </button>
        </div>
      </div>
      <div className="scenecontainer">
        {Object.entries(scenes)
          .filter((scene) => scene[1].group === groupId)
          .map(([id, scene]) => (
            <div
              key={id}
              className="scene"
              style={{
                background: `url(${nightsky})`,
                backgroundSize: "cover",
              }}
              onClick={() => applyScene(id)}
            >
              <div className="dimmer">
                {Object.entries(scene.lightstates)
                  .filter((item, index) => index < 5)
                  .map(([light, state]) => (
                    <div
                      key={light}
                      className="color"
                      style={{ background: `${getStyle(state)}` }}
                      onClick={() => applyLightState(light, state)}
                    ></div>
                  ))}
                <div className="name">{scene.name}</div>
              </div>
              <div className="dynamiccontrol">
                <i className="far fa-play-circle"></i>
              </div>
            </div>
          ))}
      </div>
    </Modal>
  );
};

export default Scenes;
