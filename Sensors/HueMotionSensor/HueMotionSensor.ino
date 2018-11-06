#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

extern "C" {
#include "user_interface.h"
}

ADC_MODE(ADC_VCC);

/// BEGIN SETUP SENSOR PARAMETERS ///

const char* ssid = "WiFi name";
const char* password = "WiFi password";

//Set bridge ip
const char* bridgeIp = "192.168.xxx.xxx";

// depending on photoresistor you need to setup this value to trigger dark state when light level in room become low enough
#define lightmultiplier 30
// depending on device, increase or decrease the value if the device don't enter in powersave mode when battery voltage is ~3.2v
#define shutdown_voltage 2.9

// set the sensor ip address on the network (mandatory)
IPAddress strip_ip ( 192,  168,   0,  97);
IPAddress gateway_ip ( 192,  168,   0,   1);
IPAddress subnet_mask(255, 255, 255,   0);

/// END SETUP SENSOR PARAMETERS ////

uint32_t rtcData;
byte mac[6];


void goingToSleep(bool rfMode = true) {
  yield();
  delay(100);
  if (rfMode) {
    ESP.deepSleep(0, WAKE_RF_DEFAULT); //30 seconds until next alert
  } else {
    ESP.deepSleep(0, WAKE_RF_DISABLED); //20 minutes
  }
  yield();
  delay(100);
}

void blinkLed(uint8_t count) {
  for (uint8_t i = 0; i <= count; i++) {
    digitalWrite(2, LOW);
    delay(100);
    digitalWrite(2, HIGH);
    delay(100);
  }
}

void batteryMonitor() {
  if (ESP.getVcc() / 1024 <= shutdown_voltage) {
    rtcData = 1;
    blinkLed(3);
    ESP.rtcUserMemoryWrite(0, &rtcData, sizeof(rtcData));
    goingToSleep(false);
  } else {
    rtcData = 0;
    ESP.rtcUserMemoryWrite(0, &rtcData, sizeof(rtcData));
    goingToSleep();
  }
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

void sendRequest(int lightlevel) {
  String url = "/switch?mac=" + macToStr(mac);
  url += "&presence=true";
  url += "&lightlevel=" + String(lightlevel);
  if (lightlevel < 16000) {
    url += "&dark=true";
  } else {
    url += "&dark=false";
  }
  if (lightlevel > 23000) {
    url += "&daylight=true";
  } else {
    url += "&daylight=false";
  }

  WiFiClient client;

  client.connect(bridgeIp, 80);
  client.print(String("GET ") + url + " HTTP/1.1\r\n" +
               "Host: " + bridgeIp + "\r\n" +
               "Connection: close\r\n\r\n");
}


void setup() {
  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);
  ESP.rtcUserMemoryRead(0, &rtcData, sizeof(rtcData));
  if (rtcData == 1) {
    batteryMonitor();
  }
  pinMode(A0, INPUT);
  pinMode(4, INPUT);
  pinMode(5, OUTPUT);
  digitalWrite(5, HIGH);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
  WiFi.macAddress(mac);

  while (WiFi.status() != WL_CONNECTED) {
    delay(20);
  }

  if (digitalRead(4) == HIGH) {
    ArduinoOTA.begin();
    blinkLed(5);
  } else {

    rst_info *rinfo;
    rinfo = ESP.getResetInfoPtr();

    if ((*rinfo).reason != REASON_DEEP_SLEEP_AWAKE) {

      WiFiClient client;
      client.connect(bridgeIp, 80);

      //register device
      String url = "/switch";
      url += "?devicetype=ZLLPresence";
      url += "&mac=" + macToStr(mac);

      //###Registering device
      client.connect(bridgeIp, 80);
      client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                   "Host: " + bridgeIp + "\r\n" +
                   "Connection: close\r\n\r\n");
    } else {
      sendRequest(analogRead(A0) * lightmultiplier);
    }
    batteryMonitor();
  }
}

void loop() {
  ArduinoOTA.handle();
}
