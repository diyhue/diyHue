def updateGroupStats(light, lights, groups): #set group stats based on lights status in that group
    for group in groups:
        if "lights" in groups[group] and light in groups[group]["lights"]:
            for key, value in lights[light]["state"].items():
                if key in ["bri", "xy", "ct", "hue", "sat"]:
                    groups[group]["action"][key] = value
            any_on = False
            all_on = True
            for group_light in groups[group]["lights"]:
                if group_light in lights and lights[group_light]["state"]["on"]:
                    any_on = True
                else:
                    all_on = False
            groups[group]["state"] = {"any_on": any_on, "all_on": all_on,}
            groups[group]["action"]["on"] = any_on
