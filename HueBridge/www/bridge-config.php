<?php
$dbip = '127.0.0.1';
$dbname = 'hue';
$dbuser = 'hue';
$dbpass = 'hue123';

$ip_addres = $_SERVER['SERVER_ADDR'];
$gateway_interface = explode(" ", str_replace("\n", "", shell_exec('ip route | awk \'/^default/ { print $3 " " $5}\'')));
$gateway = $gateway_interface[0];
$mac = str_replace("\n", "", shell_exec('cat /sys/class/net/'.$gateway_interface[1].'/address'));

// if for some reasons shell scripts cannot retrive the correct ip, gateway and mac address of primaty interface then you must srtup them manually
//$ip_addres = xxx.xxx.xxx.xxx;
//$gateway = xxx.xxx.xxx.xxx;
//$mac = xx:xx:xx:xx:xx:xx;

?>

