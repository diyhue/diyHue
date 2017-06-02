#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

extern "C" {
#include "gpio.h"
#include "user_interface.h"
}


const char* ssid = "MikroTik";
const char* password = "nustiuceparola";
const char* switchType = "ZLLPresence";

//Set bridge ip or ip of every light controlled by this switch

const char* bridgeIp = "192.168.10.200";

IPAddress strip_ip ( 192,  168,   10,  97);
IPAddress gateway_ip ( 192,  168,   10,   1);
IPAddress subnet_mask(255, 255, 255,   0);

int counter;
byte mac[6];

void goingToSleep() {
  yield();
  delay(100);
  ESP.deepSleep(0);
  yield();
}

String macToStr(const uint8_t* mac) {
  String result;
  for (int i = 0; i < 6; ++i) {
    result += String(mac[i], 16);
    if (i < 5)
      result += ':';
  }
  return result;
}


void setup() {

  pinMode(5, INPUT);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
  WiFi.macAddress(mac);

  while (WiFi.status() != WL_CONNECTED) {
    delay(20);
  }

  rst_info *rinfo;
  rinfo = ESP.getResetInfoPtr();


  WiFiClient client;
  client.connect(bridgeIp, 80);

  //register device
  String url = "/switch?mac=" + macToStr(mac);
  if ((*rinfo).reason != REASON_DEEP_SLEEP_AWAKE) {
    url += "&devicetype=" + (String)switchType;
  } else {
    if (digitalRead(5) == HIGH) {
      url += "&presence=true";
    } else {
      url += "&presence=false";
    }
  }

  //###Registering device
  client.connect(bridgeIp, 80);
  client.print(String("GET ") + url + " HTTP/1.1\r\n" +
               "Host: " + bridgeIp + "\r\n" +
               "Connection: close\r\n\r\n");

}

void loop() {
  goingToSleep();
  delay(200);
}
