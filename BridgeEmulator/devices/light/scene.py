import configManager

bridge_config = configManager.bridgeConfig.json_config #all super temp stuff while moving/very jank

def switchScene(group, direction):
    group_scenes = []
    current_position = -1
    possible_current_position = -1 # used in case the brigtness was changes and will be no perfect match (scene lightstates vs light states)
    break_next = False
    for scene in bridge_config["scenes"]:
        if bridge_config["groups"][group]["lights"][0] in bridge_config["scenes"][scene]["lights"]:
            group_scenes.append(scene)
            if break_next: # don't lose time as this is the scene we need
                break
            is_current_scene = True
            is_possible_current_scene = True
            for light in bridge_config["scenes"][scene]["lightstates"]:
                for key in bridge_config["scenes"][scene]["lightstates"][light].keys():
                    if key == "xy":
                        if not bridge_config["scenes"][scene]["lightstates"][light]["xy"][0] == bridge_config["lights"][light]["state"]["xy"][0] and not bridge_config["scenes"][scene]["lightstates"][light]["xy"][1] == bridge_config["lights"][light]["state"]["xy"][1]:
                            is_current_scene = False
                    else:
                        if not bridge_config["scenes"][scene]["lightstates"][light][key] == bridge_config["lights"][light]["state"][key]:
                            is_current_scene = False
                            if not key == "bri":
                                is_possible_current_scene = False
            if is_current_scene:
                current_position = len(group_scenes) -1
                if direction == -1 and len(group_scenes) != 1:
                    break
                elif len(group_scenes) != 1:
                    break_next = True
            elif  is_possible_current_scene:
                possible_current_position = len(group_scenes) -1

    matched_scene = ""
    if current_position + possible_current_position == -2:
        logging.info("current scene not found, reset to zero")
        if len(group_scenes) != 0:
            matched_scene = group_scenes[0]
        else:
            logging.info("error, no scenes found")
            return
    elif current_position != -1:
        if len(group_scenes) -1 < current_position + direction:
            matched_scene = group_scenes[0]
        else:
            matched_scene = group_scenes[current_position + direction]
    elif possible_current_position != -1:
        if len(group_scenes) -1 < possible_current_position + direction:
            matched_scene = group_scenes[0]
        else:
            matched_scene = group_scenes[possible_current_position + direction]
    logging.info("matched scene " + bridge_config["scenes"][matched_scene]["name"])

    for light in bridge_config["scenes"][matched_scene]["lights"]:
        bridge_config["lights"][light]["state"].update(bridge_config["scenes"][matched_scene]["lightstates"][light])
        if "xy" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" or "sat" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "hs"
        sendLightRequest(light, bridge_config["scenes"][matched_scene]["lightstates"][light], bridge_config["lights"], bridge_config["lights_address"])
        updateGroupStats(light, bridge_config["lights"], bridge_config["groups"])
