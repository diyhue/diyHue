I create this project in order to have all lights in my house remotely managed. I choose Philips Hue API because there are lot of smartphone applications available and official one looks very good.
HUE bridge is created in PHP with mysql database as backend for storing data. For tests i use a Raspberry Pi and OrangePi Zero, both are working with no lag.

Light controllers are ESP8266 based devices. Is possible to setup more lights per strip to create nice scenes. Bridge is able to autodiscover lights on same network

Currently there is support just for rgb and rgbw neo pixel strips (library used: https://github.com/Makuna/NeoPixelBus)

Demo video: https://www.youtube.com/watch?v=izCzEavYxUY&t=198s

#TO DO:
 - create sensors and switches with ESP8266 platforms.  
 - add support for cheap wi-fi light bulbs that are available on aliexpress  
 - make scheduler function to work on bridge, currently no cron implemented.  

#BRIDGE INSTALLATION (raspbian/ubuntu/debian)  
###install webserver (apache + php)###  
sudo apt install apache2 php7.0 php7.0-mysqli php7.0-curl nmap  
or for debian distributions  
sudo apt install apache2 php5 php5-mysql php5-curl nmap  
###install database (mysql or mariadb)###  
sudo apt install mariadb-server  
   or  
sudo apt install mysql-server    
###enable rewrite module###  
sudo a2enmod rewrite  
###edit apache config###  
vim /etc/apache2/apache2.conf  
find:  
<Directory /var/www/>  
        Options Indexes FollowSymLinks  
        AllowOverride None  
        Require all granted  
</Directory>  

change "AllowOverride None"  in "AllowOverride All"  
###copy php files in /var/www/html###  
cp -r HueBridge/www/* /var/www/html  

###edit the settings variables in entryPoint.php###  
vim /var/www/html/entryPoint.php:  
  - $dbip = '127.0.0.1'; // put yout database server ip. Usualy 127.0.0.1
  - $dbname = 'hue';  //database name. default "hue" created with sql_schema.sql.  
  - $dbuser = 'hue';  //username for connection to database, default hue created with sql_schema.sql  
  - $dbpass = 'hue123';  //user password, default 'hue123'  
  - $ip_addres = '192.168.10.24';  //ip of the bridge (required by some application to work)  
  - $gateway = '192.168.10.1';  //ip of the bridge (required by some application to work)  
  - $mac = '12:1F:CF:F6:90:75';  // bridge mac address (required by some application to work)  
###import sql_schema in database###  
mysql -u username -p  < file.sql
###connect to bridge###  
open official smartphone application, click help, insert the bridge ip and connect.  

#LIGHT STRIPS  
supported neopixel led are WS2812B (rgb, recommended until a more complex rgb -> rgbw conversion will be implemented) and SK6812 (rgbw).  
data in pin must be connected to dedicated harware pin of the esp8266 platforms (rx pin on wemos d1 mini and nodemcu)  
compilation require Makuna/NeoPixelBus library that can be downloaded automatically from Arduino library mannager.  
Options in skeches:
 - const char* ssid = "...."; wi-fi where to connect
 - const char* password = "...."; wi-fi password
 - #define lightsCount x number of emulated lights per strip
 - #define pixelCount xx number of leds in strip
 - IPAddress strip_ip ( xxx,  xxx,   xxx,  xxx); to setup static ip, default commented. neet to be uncommented with gateway_ip, subnet_mask and WiFi.config(strip_ip, gateway_ip, subnet_mask);
lights can be controlled with any browser. example url:  
"http://{light ip}/set?light=1&r=0&g=60&b=255&fade=2000"  
"http://{light ip}/off?light=1&fade=1000"  
"http://{light ip}/on?light=1"  
"http://{light ip}/discover"  


#CHANGELOG

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

Credits: probonopd
