[![license](https://img.shields.io/badge/license-GPLv3%2FApache%202.0%2FCC%20BY--SA%204.0-blue.svg)](https://github.com/diyhue/diyHue/blob/master/LICENSE.md)
[![CommitActivity](https://img.shields.io/github/commit-activity/y/diyhue/diyhue.svg)](https://github.com/diyhue/diyHue/commits/master)
[![ZenHub](https://raw.githubusercontent.com/ZenHubIO/support/master/zenhub-badge.png)](https://zenhub.com)

[![JoinSlack](https://img.shields.io/badge/Join%20us-on%20Slack-green.svg)](https://join.slack.com/t/diyhue/shared_invite/enQtNzAwNDE1NDY2MzQxLTljNGMwZmE0OWRhNDIwM2FjOGM1ZTcxNjNmYjc5ZmE3MjZlNmNjMmUzYmRkZjhhOGNjOTc4NzA0MGVkYzE2NWM) [![SlackStatus](https://slackinvite.squishedmooo.com/badge.svg?colorB=8ebc06)](https://slackinvite.squishedmooo.com/)

[![Build Status](https://travis-ci.com/diyhue/diyHue.svg?branch=master)](https://travis-ci.com/diyhue/diyHue)
[![DockerPulls](https://img.shields.io/docker/pulls/diyhue/core.svg)](https://hub.docker.com/r/diyhue/core/)

[![](https://images.microbadger.com/badges/version/diyhue/core:arm.svg)](https://microbadger.com/images/diyhue/core:arm "Get your own version badge on microbadger.com")
[![](https://images.microbadger.com/badges/image/diyhue/core:arm.svg)](https://microbadger.com/images/diyhue/core:arm "Get your own image badge on microbadger.com")

[![](https://images.microbadger.com/badges/version/diyhue/core:amd64.svg)](https://microbadger.com/images/diyhue/core:amd64 "Get your own version badge on microbadger.com")
[![](https://images.microbadger.com/badges/image/diyhue/core:amd64.svg)](https://microbadger.com/images/diyhue/core:amd64 "Get your own image badge on microbadger.com")

This project emulates a Philips Hue Bridge that is able to control ZigBee lights (using Raspbee module, original Hue Bridge or IKEA Trådfri Gateway), Mi-Light bulbs (using MiLight Hub), Neopixel strips (WS2812B and SK6812) and any cheap ESP8266 based bulb by replacing the firmware with a custom one. It is written in Python and will run on all small devices such as the Raspberry Pi. Arduino sketches are provided for the Hue Dimmer Switch, Hue Tap Switch and Hue Motion Sensor. Lights are two-way synchronized so any change made from original Philips/Trådfri sensors and switches will also be applied to the bridge emulator.

![diyHue ecosystem](https://raw.githubusercontent.com/diyhue/diyhue.github.io/master/assets/images/hue-map.png)

## Getting Started
All documentation and instructions can be found over at [diyhue.readthedocs.io](https://diyhue.readthedocs.io/)

## Requirements:
 - Python 3
 - Nmap package for esp8266 lights autodiscover ```sudo apt install nmap```
 - Python ws4py package only if zigbee module is used ```sudo pip install ws4py```
 
 or
 - Docker ;-)


## To Do
 - ~~Improve web interface~~
 - esp8266 alarm horn (+schematic)
 - esp8266 IR controller 
 - ~~Working directly with ZigBee lights, switches and sensors with RaspBee module~~
 - ~~control IKEA Trådfri lights from HUE applications~~
 - ~~Create ESP8266 bridge device to add MI Lights to Hue Bridge emulator.~~
 - ~~On/Off control for other home devices using virtual lights~~
 - Alarm (~~email notification~~ + eps8266 horn)
 - ~~Hue Entertainment support~~

## Working HUE features:
  - Control lights (all functions)
  - Control groups (all functions)
  - Scenes (all functions)
  - Routines
  - Wake up
  - Go to sleep
  - Switches (custom esp8266 switches)
  - Autodiscover lights
  - Hue entertainment
  
## Working devices and applications:
  - Amazon Alexa (control only the lights)
  - Logitech Harmony
  - Trådfri Gateway
  - Hue Bridge (original + other emulators)
  - Home Assistant
  - Domoticz
  - Openhab
  - Philips Ambilight TV's 
  - Kodi Hue Ambilight
  - Jeedom
  - Hue Sync for PC
 
 ## Working smartphone applications:
  - Hue (official application)
  - [Hue Essentials](https://play.google.com/store/apps/details?id=com.superthomaslab.hueessentials) - recommended
  - hueManic
  - OnSwitch
  - HueSwitcher
  - LampShade

## Not working:
  - Home & Away future from Hue app (requires remote api)
  - Google Home (requires remote api)
  - Eneco Toon (very likely it uses cloud service detection)
  
## Supported lights:
  - WS2812B and SK6812 smart led strips
  - MiLight
  - Yeelight
  - LYT8266
  - Phillips Hue
  - Ikea Trådfri
  - Pwm RGB-CCT
  - Pwm RGBW
  - Pwm RGB
  - Pwm CCT
  - Pwm Dimming (up to 6 lights for every esp8266)
  - On/Off plugs/lights (up to 6 lights for every esp8266)
  - On/Off 433Mhz devices (multiple devices for every esp8266)
 
## Stability:
All the lights in my house are controlled by this solution so the stability is very important to me as there is no turning back to classic illumination (all switches were replaced with Ikea Trådfri Remotes and holes covered). However, I don't use all the functions, so I'm unable to perform full tests on every change. What I do currently use is Deconz with all Trådfri devices (lights + sensors), Xiaomi Motion Sensor, native ESP8266 bulbs, ESP8266 + WS2812B strips, and Xiaomi YeeLight color bulbs.
  
Please post on our [Slack team](https://slackinvite.squishedmooo.com/) any other device/application that you find to work with this emulator.
  
Check the [docs](https://diyhue.readthedocs.io/) for more details.  
  
[![Youtube Demo](https://img.youtube.com/vi/c6MsG3oIehY/0.jpg)](https://www.youtube.com/watch?v=c6MsG3oIehY)

We push updates fast so if you want to be notified, just watch this repo.

Contributions are more than welcome!

Hue living color light project for 3D printing: https://www.thingiverse.com/thing:2773413

## qtHue
You also may want to see my new project [qtHue](https://github.com/mariusmotea/qtHue) that provides a simple user interface for controlling the lights.
![qtHue](https://github.com/mariusmotea/qtHue/blob/master/Screenshot.png?raw=true)

Credits:
  - [@avinashraja98](https://github.com/avinashraja98) - Hue Entertainment server
  - Federico Zivolo ([@FezVrasta](https://github.com/FezVrasta)) Internal WebGUI
  - [@J3n50m4t](https://github.com/J3n50m4t) - Yeelight integration
  - Martin Černý ([@mcer12](https://github.com/mcer12)) - Yeelight color bulb
  - probonopd https://github.com/probonopd/ESP8266HueEmulator
  - sidoh https://github.com/sidoh/esp8266_milight_hub
  - StefanBruens https://github.com/StefanBruens/ESP8266_new_pwm
  - Cédric @ticed35 for linkbutton implementation
  - [@cheesemarathon](https://github.com/cheesemarathon) - Help with Docker images
  - [@Mevel](https://github.com/Mevel) - 433Mhz devices
  - [@Nikfinn99](https://github.com/Nikfinn99) - PCB designs
  - [@crankyoldgit](https://github.com/crankyoldgit) - IR Remote library
