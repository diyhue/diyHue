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
