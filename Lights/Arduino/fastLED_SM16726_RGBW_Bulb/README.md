# FastLED RGBW Bulb

This sketch utilises the [FastLED](https://github.com/FastLED/FastLED) library in order to be able to use bulbs that don't use simple RGB PWM dimming, rather use an SPI controlled interface instead. It has only been tested on one type of such [bulb](https://www.ebay.co.uk/itm/E27-8W-RGBW-Wireless-Smart-Bulb-WiFi-APP-Remote-Control-LED-Light-for-Alexa-UK-/263504802242?item=263504802242&ViewItem=&nma=true&si=x%252BdO9TdL81nrD8N1V9CZxFXF0rY%253D&orig_cvip=true&rt=nc&_trksid=p2047675.l2557), but it should work with many similar bulbs which have CW LEDs and RGB LEDs.

Slight alterations have been made in comparison to other RGBW light sketches in this project these being:
* FastLED implementation for RGB LEDs
* PWM implementation for CW LEDs
* Ability to use [FastLED Color Correction](https://github.com/FastLED/FastLED/wiki/FastLED-Color-Correction)
* Experimental use of CW leds in XY conversion by getting a basic Luminance value and using that.
* Use of CCT bulb algorithm for ct conversion, where cold white mainly consists of the CW LEDs and the warmer whites mainly consist of RGB leds.
* Slightly different implementation of the hue conversion to also include the cold white LEDs

## Use

Depending on your bulb or strip, set these variables to their appropriate values for FastLED setup:

* DATA_PIN - Which pin is data for SPI being sent out
* CLOCK_PIN - Pin for SPI clock
* COLOR_ORDER - Order of which colors are interpreted, usually RGB
* LED_TYPE - What type of LEDs are you using, list [here](https://github.com/FastLED/FastLED/wiki/Chipset-reference)
* CORRECTION - Color correction setting for LEDs, list of options [here](http://fastled.io/docs/3.1/group___color_enums.html)

## Problems

* There is flickering from the white LEDs when changing values in the XY color picker in the hue app. To stop this behaviour set `W_ON_XY` to false. 
* There is also a bit of an issue around the blue color area when using the white color leds on the color picker.
* Don't think the infoLight is working.

## To Do

* Think about implementing FastLEDs native dimming functions.
 Try to solve above problems.
