import axios from "axios";

const applyScene = (user, scene) => {
axios
  .put(
    `/api/${user}/groups/0/action`,
    {'scene': scene}
  )
};

const Scenes = ({user, groupId, scenes}) => {
  console.log("group is " + groupId)
  return (
    <>
    {Object.entries(scenes).filter(scene => scene[1].group === groupId).map(([id, scene]) => (
      <div className="sceneContainer" onClick={() => applyScene(id)} key={id}>
        <p style={{color: '#ccc'}}>{scene.name}</p>
      </div>
    ))}
    <div className="clear"></div>
    </>
);
}

export default Scenes
