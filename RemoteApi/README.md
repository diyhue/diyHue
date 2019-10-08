# Remote Services

This script is responsable for following services:
 - Remote api integrated in Hue Essentials
 - Remote discovery 
 
 
 ## Remote API
 
 ### Configuration
 
 Remote api is disabled by defult in diyhue. In order to turn it on you must manually edit the script HueEmulator3.py located in /opt/hue-emulator/ and 
 replace `dontBlameDiyHue = False` with `dontBlameDiyHue = True` (a service restart is require `sudo systemctl restart hue-emulator`) and also to enable remote services from Hue Essentials app.

 
 ### Security
 
 The remote api use same security futures like original Hue Remote API. Remote service store entire data in the RAM, once
 the service is restarted everithing is lost. Every device that use remote api must know the bridge uniqui apikey and also a valid
 user hash. While the apikey is send to bridge for registration every 30 second in a HTTPS GET request the user hash is sent only
 when the bridge is controlled remotelly from Hue Essentials app. No IP tracking is possible as the connection is terminated in frontend
 reverse proxy and all connections to this service are received with the proxy IP.
 
 ### Test
 
 Turn off wifi connection on you phone and open Hue Essentials app
 
 ### How is working
 
 Hue Emulator send an HTTPS GET request to bridge in a `while true` loop with bridge apikey. The remote service respond
  and keep this connection opened for 30 seconds if there is no data request in the queue for it (client timeout is set to 35 seconds). 
If an application has requested some data for a certain bridge (based on apikey) the request will be served right away containing also
the user hash. If the user hash is valid the bridge will process the request and send data back to remote service is a new HTTPS POST request. The client application connection
will be opened until the data from hue emulator will be send back the responce.



 ## Remote Discovery
 
 This is similar to official Hue remote discovery service (https://discovery.meethue.com), and can be accessed at address https://discovery.diyhue.org. Is intended to help bridge local ip detection for users that use DHCP and don't have ip reservation. Hue Essentials app use this to correct the hue emulator bridge ip in case this was changed on the network.
 






