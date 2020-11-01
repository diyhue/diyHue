def webform_hue():
    return """<!doctype html>
<html>
   <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Hue Bridge Setup</title>
      <link rel="stylesheet" href="https://unpkg.com/purecss@0.6.2/build/pure-min.css">
   </head>
   <body>
      <form class="pure-form pure-form-aligned" action="" method="get">
         <fieldset>
            <legend>Hue Bridge Setup</legend>
            <div class="pure-control-group"><label for="ip">Hub ip</label><input id="ip" name="ip" type="text" placeholder="168.168.xxx.xxx"></div>
            <div class="pure-controls">
               <label class="pure-checkbox">
               First press the link button on Hue Bridge
               </label>
               <button type="submit" class="pure-button pure-button-primary">Save</button>
            </div>
         </fieldset>
      </form>
   </body>
</html>"""
