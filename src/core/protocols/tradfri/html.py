
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
