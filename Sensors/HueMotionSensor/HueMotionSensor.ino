#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

extern "C" {
#include "gpio.h"
#include "user_interface.h"
}

/// BEGIN SETUP SENSOR PARAMETERS ///
const char* ssid = "MikroTik";
const char* password = "nustiuceparola";

//Set bridge ip
const char* bridgeIp = "192.168.10.200";

// Minutes to sleep between light level is mesured and send to bridge
const int sleepTimeS = 600;

// depending on photoresistor you need to setup this value to trigger dark state when light level in room become low enough
#define lightmultiplier 40

IPAddress strip_ip ( 192,  168,   10,  97);
IPAddress gateway_ip ( 192,  168,   10,   1);
IPAddress subnet_mask(255, 255, 255,   0);

/// END SETUP SENSOR PARAMETERS //// 

const char* switchType = "ZLLPresence";
int counter, luminance;
byte mac[6];

void goingToSleep() {
  yield();
  delay(100);
  ESP.deepSleep(sleepTimeS * 1000000);
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
  pinMode(4, OUTPUT);
  digitalWrite(4, HIGH);
  pinMode(A0, INPUT);
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

  String url = "/switch?mac=" + macToStr(mac);
  if ((*rinfo).reason != REASON_DEEP_SLEEP_AWAKE) {
    url += "&devicetype=" + (String)switchType;
  } else {

    // sent light
    luminance = (1024 - analogRead(A0)) * lightmultiplier;

    url += "&lightlevel=";
    url += String(luminance);
    if (luminance < 16000) {
      url += "&dark=true";
    } else {
      url += "&dark=false";
    }

    if (luminance > 23000) {
      url += "&daylight=true";
    } else {
      url += "&daylight=false";
    }

    if (digitalRead(5) == HIGH) {
      url += "&presence=true";
    } else {
      url += "&presence=false";
    }
  }


  client.connect(bridgeIp, 80);
  client.print(String("GET ") + url + " HTTP/1.1\r\n" +
               "Host: " + bridgeIp + "\r\n" +
               "Connection: close\r\n\r\n");

}

void loop() {
  goingToSleep();
  delay(200);
}
