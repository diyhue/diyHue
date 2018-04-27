# Lights

Supported devices are:
 - generic pwm cct lights (2 channels) - ex Milight bicolor
 - generic pwm rgb lights (3 channels)
 - generic pwm rgbw lights (4 channels) - ex. Feican bulbs
 - generic pwm rgb-cct lights (5 chnnels - ex Milight FUT015)
 - SK6812 neopixels
 - WS2812B neopixels
 - all ZigBee lights - check [Raspbee module](https://github.com/mariusmotea/diyHue/wiki/6.-Raspbee-module) page
 
 New updates are pushed just to Arduino folder, if you want to use PlatformIO just update the content of .cpp file from related arduino sketch.

Lot of Wi-Fi lights from the market are esp8266 based and can be used very easy with this project by flashing the firmware with the one provided. Almost all dimmable lights that are not esp8266 based (ex MiLight bulbs) can be converted to wifi with one esp-12s module by connecting the outputs directly to led drivers (picture available). If you decide to convert a MiLight bulb to esp-12s i recommend to use a [micro step down buck converter](https://www.aliexpress.com/item/3pcs-1A-DC-5V-6V-9V-12V-24V-to-3-3V-DC-DC-Step-Down-Buck/32765853201.html?spm=a2g0s.9042311.0.0.kDdB4j) in order to avoid overheating issues.  
All lights are two way synchronized so any change made by 3rd party device will be added also to bridge emulator on first lights group request. By default any light that become unreachable will be marked as unreachable and will be displayed as off. This is because lot of people still use classic light switches.

## Obtions in sketch  
#define light_name "WS2812 Hue Strip" - default light name used on WiFiManager and Hue-Emulator  
#define lightsCount 3  - neopixels only, represent the number of emulated lights on the strip/ring.
#define pixelCount 60  - neopixels only, is the total number of leds.

#define use_hardware_switch false // on/off state and brightness can be controlled with above gpio pins. Is mandatory to connect them to ground with 10K resistors  
#define button1_pin 4 // on and bri up  
#define button2_pin 5 // off and bri down  

WiFiManager Config Portal is configured with a timeout 120 seconds to avoid the lights being stuck in this mode

## External Libraries
 - WiFiManager
 - ArduinoJson
 - NeoPixelBus - only for neopixels

## Light GUI
![LightGUI](https://github.com/mariusmotea/diyHue/raw/master/Images/lightGUI.png)
All lights have an internal web gui that can be accesses with any browser and offer the following option:
 - turn on/off the light
 - set startup option: "Light Off" (default), "Light On" or "Last State" witch will turn on the light automatically just if last time it was on. 
 - change the scene. This will change also the power on scene
 - change any light parameter (bri, color, ct, xy, etc)

## Neopixels
Before to compile the code you must edit `lightsCount` and `pixelCount` variables. I recommend to use at last 3 lights, one light at every 20 - 50 leds so you can enjoy the Hue scenes. Data pin of the leds must be connected to RX pin of the esp8266 board.
![neopixel_wiring](https://github.com/mariusmotea/diyHue/raw/master/Images/strip_wiring_to_wemos_d1_mini.jpg)

## Generic lights
If your device is factory esp8266 based, then you must specify the pins used in that devices before to compile the code. If you don't know what pins are used or what color is controlled on a pin you can try random with OTA firmware upgrade until you match the output pin with the correct color.  
My recommendation is to use MiLight FUT15 bulbs converted to ESP-12S because of hi brightness and good color reproduction.
![MiLight FUT15](https://github.com/mariusmotea/diyHue/raw/master/Images/MiLight_RGB_CCT_converted_to_ESP-12S.jpg)

## Connect the light to Wi-Fi network
All lights are using [WiFiManager](https://github.com/tzapu/WiFiManager) and on power on will broadcast a new SSID. Connect to this network with you phone or computer and browse to [http://192.168.4.1](http://192.168.4.1) . From here you can choose you network and enter the password. After the light is present on your network open the official Hue application and scan for new lights. In case no lights are found check if nmap package is installed.

## Lights API
Lights use the same hue protocol:  
Example:  
```
PUT request 
address: "http://{light ip}/state"
json content:  
 - {"light": 2, "bri": 120}
 - {"light": 3, "on": false}
 - {"light": 2, "xy": [0.5234, 0.2353]}
 - {"ct": 483}
```

### Detection url: 
`GET` request
address: `http://{light ip}/detect`  
sample output: `{"name":"Bedroom","hue":"bulb","lights":1,"modelid":"LCT015","type":"json","mac":"26:fb:2c:a6:20:a0"}`

### Get light status
`GET` request
address: `http://{light ip}/get`  
sample output: `{"on":true,"bri":254,"xy":[0,0],"ct":447,"hue":0,"sat":0,"colormode":"ct"}`  

### List of arguments that can be passed in url:

 - "on": 1 to set light on, 0 to set the light off.
 - "x" and "y": values between 0.0 and 1.0 to setup light color in CIE chart.
 - "ct": value between 153 (max warm white) and 500 (max could white) http://en.wikipedia.org/wiki/Mired
 - hue: value between 0 and 65535, represent the hue of the light.
 - sat: saturation of the light. 255 is the most saturated and 0 is the least saturated.
 - bri: brightness of the light, 255 is the maximum brightness, 1 is the minimum, 0 will turn the light on to previews state
 - transitiontime: duration of the transition from the light’s current state to the new stat. default 4 represent 0.4 seconds.
 - bri_inc: uncrease or decrease the brightness with a specified value

## Firmware upgrade
You can upgrade the firmware very easy with Adruino OTA. Currently i doubt there will be new updates because all hue functions and lot of extra futures are implemented.
