def webformDeconz(bridge_config):
    content = """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Deconz Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Deconz Switches Setup</legend>\n"""
    for deconzSensor in bridge_config["deconz"]["sensors"].keys():
        if bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer","TRADFRI on/off switch"]:
            content += "<div class=\"pure-control-group\">\n"
            content += "<label for=\"sensor-" + deconzSensor + "\">" + bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["name"] + "</label>\n"
            content += "<select id=\"sensor-" + deconzSensor + "\" name=\"" + bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"] + "\">\n"
            if bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["modelid"] == "TRADFRI remote control":
                content += "<option value=\"ZGPSwitch\">Hue Tap Switch</option>\n"
                content += "<option value=\"ZLLSwitch\">Hue Dimmer Switch</option>\n"
            for group in bridge_config["groups"].keys():
                if "room" in bridge_config["deconz"]["sensors"][deconzSensor] and bridge_config["deconz"]["sensors"][deconzSensor]["room"] == group:
                    content += "<option value=\"" + group + "\" selected>" + bridge_config["groups"][group]["name"] + "</option>\n"
                else:
                    content += "<option value=\"" + group + "\">" + bridge_config["groups"][group]["name"] + "</option>\n"
            content += "</select>\n"
            if bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["modelid"] == "TRADFRI remote control":
                content += "<select id=\"" + deconzSensor + "\" name=\"mode_" + bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"] + "\">\n"
                content += "<option value=\"CT\">CCT Switch</option>\n"
                content += "<option value=\"SCENE\" " + ("selected" if "opmode" in bridge_config["deconz"]["sensors"][deconzSensor] and bridge_config["deconz"]["sensors"][deconzSensor]["opmode"] == "SCENE" else "") +  ">Scene Switch</option>\n"
                content += "</select>\n"
            content += "</div>\n"
    content += "<legend>Tradfri Motion Sensors Setup</legend>\n"
    for deconzSensor in bridge_config["deconz"]["sensors"].keys():
        if bridge_config["deconz"]["sensors"][deconzSensor]["modelid"] == "TRADFRI motion sensor":
            content += "<div class=\"pure-control-group\">\n"
            content += "<label for=\"sensor-" + deconzSensor + "\">" + bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["name"] + "</label>\n"
            content += "<select id=\"sensor-" + deconzSensor + "\" name=\"" + deconzSensor + "\">\n"
            content += "<option value=\"internal\"" + ("selected" if bridge_config["deconz"]["sensors"][deconzSensor]["lightsensor"] == "internal" else "") + ">Internal</option>\n"
            content += "<option value=\"astral\"" + ("selected" if bridge_config["deconz"]["sensors"][deconzSensor]["lightsensor"] == "astral" else "") + ">Astral</option>\n"
            content += "<option value=\"combined\"" + ("selected" if bridge_config["deconz"]["sensors"][deconzSensor]["lightsensor"] == "combined" else "") + ">Combined</option>\n"
            content += "<option value=\"none\"" + ("selected" if bridge_config["deconz"]["sensors"][deconzSensor]["lightsensor"] == "none" else "") + ">None</option>\n"
            content += "</select>\n"
            content += "</div>\n"
    content += """<div class="pure-controls">
<button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</div>
</fieldset>
</form>
</body>
</html>"""
    return content
