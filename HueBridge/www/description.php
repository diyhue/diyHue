<?php
require_once('bridge-config.php');

echo "<root xmlns=\"urn:schemas-upnp-org:device-1-0\">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<URLBase>http://". $ip_addres .":80/</URLBase>
<device>
<deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>
<friendlyName>Philips hue (". $_SERVER['SERVER_ADDR'] .")</friendlyName>
<manufacturer>Royal Philips Electronics</manufacturer>
<manufacturerURL>http://www.philips.com</manufacturerURL>
<modelDescription>Philips hue Personal Wireless Lighting</modelDescription>
<modelName>Philips hue bridge 2015</modelName>
<modelNumber>BSB002</modelNumber>
<modelURL>http://www.meethue.com</modelURL>
<serialNumber>" . strtoupper(str_replace(":", "",$mac)) . "</serialNumber>
<UDN>MYUUID</UDN>
<presentationURL>index.html</presentationURL>
<iconList>
<icon>
<mimetype>image/png</mimetype>
<height>48</height>
<width>48</width>
<depth>24</depth>
<url>hue_logo_0.png</url>
</icon>
<icon>
<mimetype>image/png</mimetype>
<height>120</height>
<width>120</width>
<depth>24</depth>
<url>hue_logo_3.png</url>
</icon>
</iconList>
</device>
</root>";
exit(0);
?>
