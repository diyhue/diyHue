#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

extern "C" {
#include "gpio.h"
#include "user_interface.h"
}

/// BEGIN SETUP SENSOR PARAMETERS ///
const char* ssid = "IDEMIA Office";
const char* password = "Otopeni!";

//Set bridge ip
const char* bridgeIp = "192.168.0.112";

IPAddress sensor_ip ( 192,  168,   0,  97);
IPAddress gateway_ip ( 192,  168,   0,   1);
IPAddress subnet_mask(255, 255, 255,   0);



void goingToSleep() {
  yield();
  delay(100);
  ESP.deepSleep(0);
  yield();
  delay(200);
}

void sendRequest(bool boot = true) {
  byte mac[6];
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.config(sensor_ip, gateway_ip, subnet_mask);
  WiFi.macAddress(mac);

  while (WiFi.status() != WL_CONNECTED) {
    delay(20);
  }

  String url = "/switch?mac=" + macToStr(mac);
  if (boot) {
    url += "&devicetype=ZLLPresence";
  }

  WiFiClient client;

  client.connect(bridgeIp, 80);
  client.print(String("GET ") + url + " HTTP/1.1\r\n" +
               "Host: " + bridgeIp + "\r\n" +
               "Connection: close\r\n\r\n");
}

String macToStr(const uint8_t* mac) {
  String result;
  for (uint8_t i = 0; i < 6; ++i) {
    result += String(mac[i], 16);
    if (i < 5)
      result += ':';
  }
  return result;
}


void setup() {
  rst_info *rinfo;
  rinfo = ESP.getResetInfoPtr();

  if ((*rinfo).reason != REASON_DEEP_SLEEP_AWAKE) {
    sendRequest(); //register the senzor
  } else {
    sendRequest(false);
  }

  goingToSleep();

}

void loop() { }
