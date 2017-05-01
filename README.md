## NEW HUE BRIDGE RELEASE (Python Based)
Old version based on PHP + Mysql was decommisioned. New version process rules and schedules like real Hue Bridge and don't require complex installation steps. Configuration is saved to json file and can be manually edited to create objects or change bridge settings that are not available in smartphone application.

### Requirements:
nmap package for lights autodiscover

## TO DO
 - control IKEA Trådfri lights from HUE applications
 - Create ESP8266 bridge device to add MI Lights to Hue Bridge emulator.

## LIGHT STRIPS:
Supported neopixel leds are WS2812B and SK6812 (rgbw).  
Data in pin of the leds must be connected to dedicated harware pin of the esp8266 platforms (rx pin on wemos d1 mini and esp-12e)  
Compilation require Makuna/NeoPixelBus library that can be founded and downloaded automatically from Arduino library mannager.  

## COLOR DREAM RGBW BULBS:
I found these bulbs are esp8266 based devices that can be adapted to work with this bridge. Despite the low price these bulbs feels solid, are more heavy than regular bulbs and i expect to be medium to long life.
I was not able to flash the memory by connecting vdd, gnd, rx, tx, rst and gpio0 pins to a nodemcu dev board, but was very easy for me to replace the SPI flash chip from an already programmed epb8266 board. This operation took me about 30 seconds, while soldering the small wires took me more than 5 minutes. Future firmware updates will be easy to perform via Arduino OTA (wifi). Sketch for these bulbs can be found in RgbwHueBulb folder, the gpio pins defined (12, 13, 14 and 5) are the correct ones connected to leds.
Bulbs where buyed from here:
https://www.aliexpress.com/item/AC85-240V-5W-7W-9W-RGBW-WIFI-LED-Bulb-Light-Colorful-Dimmable-LED-Light-Support-IOS/32785628736.html?spm=2114.13010608.0.0.B8FcLh

#### Options in skeches:
 - ```const char* ssid = "....";``` // your wi-fi netwotk mane
 - ```const char* password = "....";```// your wi-fi password
 - ```lightsCount x ``` //number of emulated lights per strip
 - ```pixelCount xx``` // number of leds in strip
 - ```default_scene x``` // available scenes: 0 = Relax, 1 = Read, 2 = Concentrate, 3 = Energize, 4 = Dimmed, 5 = Bright, 6 = Night
 - ```startup_on false/true```// true = light will start of power, like regular bulbs with default_scene
 - ```IPAddress strip_ip ( xxx,  xxx,   xxx,  xxx);``` //if you want to use static ip uncommented with gateway_ip, subnet_mask and WiFi.config(strip_ip, gateway_ip, subnet_mask);
lights can be controlled with any browser. example url:  
```
"http://{light ip}/set?light=1&r=0&g=60&b=255&transitiontime=2000"
"http://{light ip}/discover"
```
list of arguments that can be passed in url:
  - "on": 1 to set light on, 0 to set the light off.
  - "r", "g", "b": setup light color using rbg values between 0 and 255.
  - "x" and "y": values between 0.0 and 1.0 to setup light color in CIE chart.
  - "ct": value between 153 (max warm white) and 500 (max could white) http://en.wikipedia.org/wiki/Mired
  - hue: value between 0 and 65535, represent the hue of the light.
  - sat: saturation of the light. 255 is the most saturated and 0 is the least saturated.
  - bri: brightness of the light, 255 is the maximum brightness, 1 is the minimum, 0 will turn the light on to previews state
  - transitiontime: duration of the transition from the light’s current state to the new stat. default 4 represent 0.4 seconds.
  - bri_inc: uncrease or decrease the brightness with a specified value
## CHANGELOG

24-Mar-2017  
 - improve color acuracy  
 - light strips are automaticaly detected and can be configured from official application  
 - sql schema create also the user hue@127.0.0.1

25-Mar-2017
 - switch light discover to nmap, network scanning is done much faster.
 - on new light scan check if ip of current ones was changed. if yes update in database with new ip
 - option for static ip on lights
 - new arduino skeches where lights are default on. Useful if are still used classic wall switches.

25-Mar-2017  
 - fix group rename bug

28-Mar-2017  
 - fix light delete bug  
 - merged arduino skeches, now default on can be set with header options "startup_brightness" and "startup_color"

29-Mar-2017  
 - add new arduino sketch that bring support for pwm rgb lights

01-Apr-2017  
 - fix scheduler delete bug
 - add cron job file, now "My routines" from application are working. Still issues with "Wake up" and "Go to sleep"
 - add rgbw sketch for "Dream Color" wifi RGBW bulb

07-Apr-2017
 - Major changes and improvements. Color processing is made now by light instead of bridge, for this reason lights must be also updated.
 - Was created first sensor concept skech that run in deep sleep mode.

15-Apr-2017
 - Added SSDP discover python script.
 - ip, gateway and mac are automaticaly retrived from host.

01-May-2017
 - Rerwire Hue Bridge Emulator to Python

Contributions are welcomed  

Credits: probonopd
