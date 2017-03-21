I create this project in order to have all lights in my house remotely managed. I choose Philips Hue API because there are lot of smartphone applications available and official one looks very good. 
HUE bridge is created in PHP with mysql database as backend for storing data. For tests i use a Raspberry Pi. There is no configuration panel, lights ip's must be chaged directly in dababase (phpMyAdmin is nice to have). Other settings must be changes in entryPoint.php. There is no SSDP discover service but most application support direct ip connection (official one from Help button).

Light controllers are ESP8266 based devices. Is possible to setup more lights per strip to create nice scenes. 

Currently there is support just for rgb and rgbw neo pixel strips (library used: https://github.com/Makuna/NeoPixelBus)

TO DO:
 - create sensors and switches with ESP8266.
 - make schedules functions to work on bridge.

BRIDGE INSTALLATION (raspbian/ubuntu/debian)

sudo apt install apache2 php7.0 php7.0-mysqli php7.0-curl
sudo apt install mariadb-server
   or 
sudo apt install mysql-server
sudo a2enmod rewrite
copy www folder content to /var/www/html
edit the folowing variables in entryPoint.php:
  - $dbip = '192.168.10.111';
  - $dbname = 'hue';
  - $dbuser = 'hue';
  - $dbpass = 'hue123';
  - $ip_addres = '192.168.10.13';
  - $gateway = '192.168.10.1';
  - $mac = '12:1F:CF:F6:90:75';
import sql_schema in database

 
 Credits: probonopd
