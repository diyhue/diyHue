#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

extern "C" {
#include "gpio.h"
#include "user_interface.h"
}

/// BEGIN SETUP SENSOR PARAMETERS ///
const char* ssid = "wifi-name";
const char* password = "wifi-pass";

//Set bridge ip
const char* bridgeIp = "192.168.10.200";

// seconds to sleep between light level is mesured and sent to bridge
const int sleepTimeS = 1200; // 1200 seconds => 20 minutes

// depending on photoresistor you need to setup this value to trigger dark state when light level in room become low enough
#define lightmultiplier 30

//static ip configuration is necessary to minimize bootup time from deep sleep
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);

/// END SETUP SENSOR PARAMETERS ////

int counter;
byte rtcStore[6];


void goingToSleep(int seepSeconds, bool sleepRfMode) {
  yield();
  delay(100);
  if (sleepRfMode) {
    ESP.deepSleep(seepSeconds * 1000000, WAKE_RF_DISABLED);
  } else {
    ESP.deepSleep(1, WAKE_RF_DEFAULT);
  }
  yield();
  delay(200);
}

void sendRequest(uint8_t op) {
  byte mac[6];
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
  WiFi.macAddress(mac);

  while (WiFi.status() != WL_CONNECTED) {
    delay(20);
  }

  String url = "/switch?mac=" + macToStr(mac);
  if (op == 0) {
    url += "&devicetype=ZLLPresence";
  } else if (op == 1) {
    rtcStore[1] = 1;
    url += "&presence=true";
  } else if (op == 2) {
    rtcStore[1] = 0;
    url += "&presence=false";
  } else if (op == 3) {

    int lightlevel = ((255 * rtcStore[4]) + rtcStore[5]) * lightmultiplier;

    url += "&lightlevel=";
    url += String(lightlevel);
    if (lightlevel < 16000) {
      url += "&dark=true";
      rtcStore[3] = 1;
    } else {
      url += "&dark=false";
      rtcStore[3] = 0;
    }

    if (lightlevel > 23000) {
      url += "&daylight=true";
    } else {
      url += "&daylight=false";
    }
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
  system_rtc_mem_read(64, rtcStore, 6);
  if (rtcStore[0] == 1) {
    // wake up in rf mode
    rtcStore[0] = 0;
    sendRequest(rtcStore[1]);
    system_rtc_mem_write(64, rtcStore, 6);
    if (rtcStore[2] == 1) {
      goingToSleep(30, true);
    } else {
      goingToSleep(sleepTimeS, true);
    }

  } else {
    //wake up in non rf mode to avoid rf interferences
    pinMode(4, OUTPUT);
    digitalWrite(4, HIGH);
    pinMode(5, INPUT);
    pinMode(A0, INPUT);
    rtcStore[0] = 1;

    rst_info *rinfo;
    rinfo = ESP.getResetInfoPtr();
    uint8_t operation;

    if ((*rinfo).reason != REASON_DEEP_SLEEP_AWAKE) {
      operation = 0; //register the senzor
    } else if (digitalRead(5) == HIGH) {
      if (rtcStore[2] == 0) {
        operation = 1;
        rtcStore[2] = 1;
      } else {
        if (rtcStore[3]  == 0) {
          operation = 3;
        } else {
          //check again in 30seconds
          goingToSleep(30, true);
        }
      }
    } else {
      if (rtcStore[2] == 0) {
        operation = 3;
      } else {
        operation = 2;
        rtcStore[2] = 0;
      }
      delay(1000);
    }

    if (operation == 3) {
      int luminance = analogRead(A0);
      rtcStore[4] = 0;
      while (luminance > 255) {
        luminance -= 255;
        rtcStore[4]++;
      }
      rtcStore[5] = luminance;
    }

    rtcStore[1] = operation;

    system_rtc_mem_write(64, rtcStore, 6);

    //reboot in rf mode
    goingToSleep(0, false);

  }
}

void loop() { }
