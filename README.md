I create this project in order to have all lights in my house remotely managed. I choose Philips Hue API because there are lot of smartphone applications available and official one looks very good. 
HUE bridge is created in PHP with mysql database as backend for storing data. For tests i use a Raspberry Pi and OrangePi Zero. There is no configuration panel, lights ip's must be chaged directly in dababase (phpMyAdmin is nice to have). Other settings must be changes in entryPoint.php. There is no SSDP discover service but most application support direct ip connection (official one from Help button).

Light controllers are ESP8266 based devices. Is possible to setup more lights per strip to create nice scenes. 

Currently there is support just for rgb and rgbw neo pixel strips (library used: https://github.com/Makuna/NeoPixelBus)

TO DO:
 - create sensors and switches with ESP8266.  
 - make schedules functions to work on bridge.  

BRIDGE INSTALLATION (raspbian/ubuntu/debian)  
###install webserver (apache + php)###  
sudo apt install apache2 php7.0 php7.0-mysqli php7.0-curl  
or for debian distributions  
sudo apt install apache2 php5 php5-mysql php5-curl  
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
cp -r /var/www/html  

###edit the settings variables in entryPoint.php###  
vim /var/www/html/entryPoint.php:  
  - $dbip = '192.168.10.111'; // put yout database server ip. Usualy 127.0.0.1 
  - $dbname = 'hue';  //database name. default "hue".  
  - $dbuser = 'hue';  //username for connection to database  
  - $dbpass = 'hue123';  //user password  
  - $ip_addres = '192.168.10.13';  //ip of the bridge (required by some application to work)  
  - $gateway = '192.168.10.1';  //ip of the bridge (required by some application to work)  
  - $mac = '12:1F:CF:F6:90:75';  // bridge mac address (required by some application to work)  
###import sql_schema in database###  
### edit following database tables###  
edit lights.ip and light.strip_light_nr tables. One strip can emulate multiple lights (lightsCount variable in sketches, default 3)  
###connect to bridge###  
open official smartphone application, click help, insert the bridge ip and connect.  

LIGHT STRIPS  
supported neopixel led are WS2812B (rgb, recommended) and SK6812 (rgbw).  
data in pin must be connected to dedicated harware pin of the esp8266 platforms (rx pin on wemos d1 mini and nodemcu)  
compilation require Makuna/NeoPixelBus library that can be downloaded automatically from Arduino library mannager.  
lights can be controlled with any browser. example url:  
"http://{light ip}/set?light=1&r=0&g=60&b=255&fade=2000"  
"http://{light ip}/off?light=1&fade=1000"  
"http://{light ip}/on?light=1"  

 
Credits: probonopd
