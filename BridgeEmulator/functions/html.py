def description(ip, mac):
    return """<?xml version="1.0" encoding="UTF-8" ?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<URLBase>http://""" + ip + """:80/</URLBase>
<device>
<deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>
<friendlyName>Philips hue (""" + ip + """)</friendlyName>
<manufacturer>Royal Philips Electronics</manufacturer>
<manufacturerURL>http://www.philips.com</manufacturerURL>
<modelDescription>Philips hue Personal Wireless Lighting</modelDescription>
<modelName>Philips hue bridge 2015</modelName>
<modelNumber>BSB002</modelNumber>
<modelURL>http://www.meethue.com</modelURL>
<serialNumber>""" + mac + """</serialNumber>
<UDN>uuid:2f402f80-da50-11e1-9b23-""" + mac + """</UDN>
<presentationURL>index.html</presentationURL>
<iconList>
<icon>
<mimetype>image/png</mimetype>
<height>48</height>
<width>48</width>
<depth>24</depth>
<url>hue_logo_0.png</url>
</icon>
</iconList>
</device>
</root>
"""

def webformTradfri():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Tradfri Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Tradfri Setup</legend>
<div class=\"pure-control-group\"><label for=\"ip\">Bridge IP</label><input id=\"ip\" name=\"ip\" type=\"text\" placeholder=\"168.168.xxx.xxx\"></div>
<div class=\"pure-control-group\"><label for=\"code\">Security Code</label><input id=\"code\" name=\"code\" type=\"text\" placeholder=\"1a2b3c4d5e6f7g8h\"></div>
<div class=\"pure-controls\"><label for=\"cb\" class=\"pure-checkbox\"></label><button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</fieldset>
</form>
</body>
</html>"""


def webform_milight():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Milight Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Milight Setup</legend>
<div class=\"pure-control-group\"><label for=\"ip\">Hub ip</label><input id=\"ip\" name=\"ip\" type=\"text\" placeholder=\"168.168.xxx.xxx\"></div>
<div class=\"pure-control-group\"><label for=\"device_id\">Device id</label><input id=\"device_id\" name=\"device_id\" type=\"text\" placeholder=\"0x1234\"></div>
<div class=\"pure-control-group\">
<label for=\"mode\">Mode</label>
<select id=\"mode\" name=\"mode\">
<option value=\"rgbw\">RGBW</option>
<option value=\"cct\">CCT</option>
<option value=\"rgb_cct\">RGB+CCT</option>
<option value=\"rgb\">RGB</option>
</select>
</div>
<div class=\"pure-control-group\">
<label for=\"group\">Group</label>
<select id=\"group\" name=\"group\">
<option value=\"1\">1</option>
<option value=\"2\">2</option>
<option value=\"3\">3</option>
<option value=\"4\">4</option>
</select>
</div>
<div class=\"pure-controls\"><button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</fieldset>
</form>
</body>
</html>"""

def webform_hue():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Hue Bridge Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Hue Bridge Setup</legend>
<div class=\"pure-control-group\"><label for=\"ip\">Hub ip</label><input id=\"ip\" name=\"ip\" type=\"text\" placeholder=\"168.168.xxx.xxx\"></div>
<div class=\"pure-controls\">
<label class="pure-checkbox">
First press the link button on Hue Bridge
</label>
<button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</fieldset>
</form>
</body>
</html>"""

def webform_linkbutton():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Hue LinkButton</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Hue LinkButton</legend>

<div class="pure-control-group">
<label for="username">Username</label><input id="username" name="username" type="text" placeholder="Hue" data-cip-id="username">
</div>
<div class="pure-control-group">
<label for="password">Password</label><input id="password" name="password" type="password" placeholder="HuePassword" data-cip-id="password">
</div>

<div class=\"pure-controls\">
<label class="pure-checkbox">
Click on Activate button to allow association for 30 sec.
</label>
<input class=\"pure-button pure-button-primary\" type=\"submit\" name=\"action\" value=\"Activate\">
<input class=\"pure-button pure-button-primary\" type=\"submit\" name=\"action\" value=\"ChangePassword\">
<input class=\"pure-button pure-button-primary\" type=\"submit\" name=\"action\" value=\"Exit\"></div>
</fieldset>
</form>
</body>
</html>"""

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
        if bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
            content += "<div class=\"pure-control-group\">\n"
            content += "<label for=\"" + deconzSensor + "\">" + bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["name"] + "</label>\n"
            content += "<select id=\"" + deconzSensor + "\" name=\"" + bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"] + "\">\n"
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
    content += """<div class="pure-controls">
<button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</div>
</fieldset>
</form>
</body>
</html>"""
    return content
