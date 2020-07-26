# Remote Services

This script is responsible for following services:
 - Remote API integration with Hue Essentials
 - Remote discovery 
 
 
 ## Remote API
 
 ### Configuration
 
 Remote API is disabled by default in diyHue. In order to turn it on you need to enable Away from Home in the Hue Essentials app.

 
 ### Security
 
 The remote API uses the same security features like the original Hue Remote API. The remote service stores the entire data in RAM, once the service is restarted everything is lost. Every device that uses remote API must know the bridge unique apikey and also a valid user hash. The apikey is sent to the bridge for registration every 30 second in a HTTPS GET request. The user hash is sent only when the bridge is controlled remotely by the Hue Essentials app. No IP tracking is possible as the connection is terminated in frontend reverse proxy and all connections to this service are received with the proxy IP.
 
 ### Test
 
 Turn off WiFi connection on your phone and open the Hue Essentials app.
 
 ### How is working
 
 Hue Emulator send a HTTPS GET request to the bridge in a `while true` loop with bridge apikey. The remote service responds and keeps this connection opened for 30 seconds, if there is no data request in the queue for it (client timeout is set to 35 seconds). If an application has requested some data for a certain bridge (based on apikey) the request will be served right away, which also contains the user hash. If the user hash is valid the bridge will process the request and send data back to remote service in a new HTTPS POST request. The client application connection will be opened until the data response from the hue emulator is sent back.



 ## Remote Discovery
 
 This is similar to the official Hue remote discovery service (https://discovery.meethue.com), and can be accessed at address https://discovery.diyhue.org. It is intended to help bridge local IP detection for users that use DHCP and don't have IP reservation. The Hue Essentials app uses this to correct the hue emulator bridge IP in case this was changed on the network.
