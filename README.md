## diyHue
With this project you will be able to control any ESP8266 based light available on the market using Philips Hue smartphone applications or from any web browser using light internal GUI. Hue Bridge Emulator is needed only if you want to control the lights from Philips Hue applications and to get the advantages of functions present in Hue Lights. Is written in python and will run on all small boxes like RaspberryPi.

### Requirements:
nmap package for lights autodiscover

## TO DO
 - control IKEA Trådfri lights from HUE applications
 - Create ESP8266 bridge device to add MI Lights to Hue Bridge emulator.

## LIGHT STRIPS:
There is support for both WS2812B (rgb) and SK6812 (rgbw) smart leds (neopixels). Data in pin of the strip must be connected to rx pin of esp8266 device. In order to compile the sketch you must download NeoPixelBus (by Makuna) and WiFiManager (by tzapu) libraries available in Arduino library manager. Is possible to emulate more lights in one strip by setting lightsCount value to any value. I recommend about 3 lights per strip in order to have nice scenes.


## GENERIC PWM LIGHTS:

Most of wifi bulbs and strip controllers from the market are esp8266 based and control the brightness of leds using pwm. The only real difference from them is the order of output pins. If you intend to buy some cheap wifi bulbs/strips and want to use this project you will need to check how hard is to flash the firmware in that light. So far i use only "Color Dreams" wifi bulbs and i was not able to flash the firmware easy using external serial adapter connected directly to ESP8266 pins. However for me was not that hard to replace the SPI flash chip from these bulbs with ones already flashed on WEMOS d1 mini pro, but i have some electronics skills and was not first time when i replace an SOT8 chip.

#### Options in skeches:
 - ```lightsCount x ``` //number of emulated lights per strip, available only for neopixels stript
 - ```pixelCount xx``` // number of leds in strip, available only for neopixels strips
 - ```IPAddress strip_ip ( xxx,  xxx,   xxx,  xxx);``` //if you want to use static ip uncommented with gateway_ip, subnet_mask and WiFi.config(strip_ip, gateway_ip, subnet_mask) line.
lights can be controlled from internal GUI or with hue api via http GET of POST. example url:  
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

17-May-2017
 - implement wifi manager for wifi setup
 - implement light GUI
 - power options are saved in EEPROM

Contributions are welcomed  

Credits: probonopd
