I create this project in order to have all lights in my house remotely managed whitout to pay the expensive price of original Philips devices. Currently all futures of original bridge are working except "Wake up" and "Go to sleep" functions (need some sample output from original bridges). I expect this to be fixed soon.
HUE bridge is created in PHP with mysql database as backend for storing data. For tests i use both an RaspberryPi 2 and an OrangePi Zero, both are working with no lag. I expect RaspberryPi Zero W to work also with no lag.

Light controllers are ESP8266 based devices (ESP-12E and WEMOS D1 mini in my tests). Is possible to setup more lights per strip to create nice scenes. Bridge is able to autodiscover lights on same network wich made the setup very easy.
Currently there is support for ws2812b and SK6812 neopixels strips and "Color Dream" wifi rgbw bulbs. 

Demo video: https://www.youtube.com/watch?v=izCzEavYxUY&t=198s (this was made before "Color Dream" bulb support

### TO DO:
 - create sensors and switches with ESP8266 platforms.  
 - add support for cheap wi-fi light bulbs that are available on aliexpress  
 - make scheduler function to work on bridge, currently no cron implemented.  
 
### BRIDGE INSTALLATION:
##### install webserver (apache + php)  
debian/raspbian distributions:  
```sh
$sudo apt install apache2 php5 php5-mysql php5-curl nmap  
```
ubuntu 16.04 distribution:  
```sh
$sudo apt install apache2 php7.0 php7.0-mysqli php7.0-curl nmap  
```
#### install database (mysql or mariadb)  
```sh
$sudo apt install mariadb-server
```
   or  
```sh
$sudo apt install mysql-server
```
#### enable rewrite module
```sh
$sudo a2enmod rewrite  
```
#### edit apache config
```sh
$sudo nano /etc/apache2/apache2.conf  
```
find:  
```sh
<Directory /var/www/>  
        Options Indexes FollowSymLinks  
        AllowOverride None  
        Require all granted  
</Directory>  
```
change ```AllowOverride None```  in ```AllowOverride All```  
#### copy php files in /var/www/html
```
$sudo cp -r HueBridge/www/. /var/www/html  
```
#### edit the settings variables in entryPoint.php 
```
$sudo nano /var/www/html/entryPoint.php:  
```
  - ```$ip_addres = '192.168.10.24';```  //replace with ip of the bridge 
  - ```$gateway = '192.168.10.1';```  //replace with the gateway/router ip   
  - ```$mac = '12:1F:CF:F6:90:75';```  // important!!! replace with bridge mac address. Cand be saw with command ```$ip a``` 
#### import sql_schema in database 
```
$mysql -u username -p  < file.sql
```
#### add cronjob for schedulers  
```
$sudo crontab -e
```
append the following line:
```
* * * * * php -f /var/www/html/cron.php
```


#### connect to bridge
Open official smartphone application, click help, insert the bridge ip and connect.
## LIGHT STRIPS:
Supported neopixel led are WS2812B (rgb, recommended until a more complex rgb -> rgbw conversion will be implemented) and SK6812 (rgbw).  
Data in pin of the leds must be connected to dedicated harware pin of the esp8266 platforms (rx pin on wemos d1 mini and esp-12e)  
Compilation require Makuna/NeoPixelBus library that can be founded and downloaded automatically from Arduino library mannager.  

## COLOR DREAM RGBW BULBS:
I found these bulbs are esp8266 based devices that can be adapted to work with this bridge. Despite the low price these bulbs feels solid, are more heavy than regular bulbs and i expect to be modium to long life.
I was not able to flash the memory by connecting vdd, gnd, rx, tx, rst and gpio0 pins to a nodemcu dev board, but was very easy for me to replace the SPI flash chip from an already programmed epb8266 board. This operation took me about 30 seconds, while soldering the small wires took me more than 5 minutes. Future firmware updates will be easy to perform via Arduino OTA (wifi). Sketch for these bulbs can be found in RgbwHueBulb folder, the gpio pins defined (12, 13, 14 and 5) are the correct ones connected to leds.
Bulbs where buyed from here:
https://www.aliexpress.com/item/AC85-240V-5W-7W-9W-RGBW-WIFI-LED-Bulb-Light-Colorful-Dimmable-LED-Light-Support-IOS/32785628736.html?spm=2114.13010608.0.0.B8FcLh

#### Options in skeches:
 - ```const char* ssid = "....";``` // your wi-fi netwotk mane
 - ```const char* password = "....";```// your wi-fi password
 - ```lightsCount x ``` //number of emulated lights per strip
 - ```pixelCount xx``` // number of leds in strip
 - ```startup_brightness 0``` // between 0 ( no light on power) and 255 (max brightness on power)
 - ```startup_color 0```// 0 = warm_white, 1 =  neutral, 2 = cold_white, 3 = red, 4 = green, 5 = blue
 - ```IPAddress strip_ip ( xxx,  xxx,   xxx,  xxx);``` //if you want to use static ip uncommented with gateway_ip, subnet_mask and WiFi.config(strip_ip, gateway_ip, subnet_mask);
lights can be controlled with any browser. example url:  
```
"http://{light ip}/set?light=1&r=0&g=60&b=255&fade=2000"  
"http://{light ip}/off?light=1&fade=1000"  
"http://{light ip}/on?light=1"  
"http://{light ip}/discover" 
```
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

Contributions are welcomed  
Credits: probonopd
