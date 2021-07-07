import axios from "axios";

const Scenes = ({ HOST_IP, api_key, groupId, scenes }) => {
  const applyScene = (scene) => {
    axios.put(`${HOST_IP}/api/${api_key}/groups/0/action`, { scene: scene });
  };

  return (
    <>
      {Object.entries(scenes)
        .filter((scene) => scene[1].group === groupId)
        .map(([id, scene]) => (
          <div
            className="sceneContainer"
            onClick={() => applyScene(id)}
            key={id}
          >
            <p style={{ color: "#ccc" }}>{scene.name}</p>
          </div>
        ))}
      <div className="clear"></div>
    </>
  );
};

export default Scenes;
