def lightsHttp():
    return """<!DOCTYPE html>
<html style="height: 100%">
   <head>
      <meta charset="utf-8">
      <link rel="stylesheet" href="https://diyhue.org/cdn/bootstrap.min.css">
      <script src="https://diyhue.org/cdn/jquery-3.3.1.min.js"></script>
   </head>
   <body>
      <table class="table">
         <thead>
            <tr>
               <th scope="col">#</th>
               <th scope="col">Name</th>
               <th scope="col">Current Version</th>
               <th scope="col">Last Vesion</th>
               <th scope="col"></th>
            </tr>
         </thead>
         <tbody>
         </tbody>
      </table>
      <script>
         jQuery.getJSON("/lights.json", function(data) {
             for (var key in data) {
             $('.table').append('<tr><th scope="row">#' + key +'</th><td>' + data[key]["name"] +'</td><td>' + data[key]["currentVersion"] +'</td><td>' + data[key]["lastVersion"] +'</td><td>' + ((data[key]["currentVersion"] < data[key]["lastVersion"]) ? '<a href="/lights?light=' + key + '&filename=' + data[key]["firmware"] +'">update</a>' : 'up to date') + '</td></tr>');
             var value = data[key];
             }
         });
      </script>
   </body>
</html>
"""

def description(ip, port, mac, name):
    return """<?xml version="1.0" encoding="UTF-8" ?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<URLBase>http://""" + ip + """:""" + str(port) + """/</URLBase>
<device>
<deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>
<friendlyName>""" + name + """ (""" + ip + """)</friendlyName>
<manufacturer>Signify</manufacturer>
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


def webform_linkbutton():
    return """<!doctype html>
<html>
   <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Hue LinkButton</title>
      <link rel="stylesheet" href="https://unpkg.com/purecss@0.6.2/build/pure-min.css">
   </head>
   <body>
      <form class="pure-form pure-form-aligned" action="" method="get">
         <fieldset>
            <legend>Hue LinkButton</legend>
            <div class="pure-control-group">
               <label for="username">Username</label><input id="username" name="username" type="text" placeholder="Hue" data-cip-id="username">
            </div>
            <div class="pure-control-group">
               <label for="password">Password</label><input id="password" name="password" type="password" placeholder="HuePassword" data-cip-id="password">
            </div>
            <div class="pure-controls">
               <label class="pure-checkbox">
               Click on Activate button to allow association for 30 sec.
               </label>
               <input class="pure-button pure-button-primary" type="submit" name="action" value="Activate">
               <input class="pure-button pure-button-primary" type="submit" name="action" value="ChangePassword">
               <input class="pure-button pure-button-primary" type="submit" name="action" value="Exit">
            </div>
         </fieldset>
      </form>
   </body>
</html>
    """
