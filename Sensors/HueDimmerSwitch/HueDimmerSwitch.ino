#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

extern "C" {
#include "gpio.h"
#include "user_interface.h"
}

#define button1_pin 4
#define button2_pin 3
#define button3_pin 13
#define button4_pin 14

const char* ssid = "WiFi name"; // replace with your wifi name
const char* password = "WiFi password"; // replace with your wifi password
const char* bridgeIp = "192.168.xxx.xxx"; //replace with the hue emulator device ip

//static ip configuration is necessary to minimize bootup time from deep sleep
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);

// Existing firmware can be updated Over the Air (OTA) by enabling Arduino ota with ON and OFF buttons placed in same time (led will flash 5 times)

/// END USER CONFIG
const char* switchType = "ZLLSwitch";
bool otaEnabled = false;



byte mac[6];
uint8_t button;

void goingToSleep() {
  yield();
  delay(100);
  ESP.deepSleep(100);
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

void sendHttpRequest(int button) {
  WiFiClient client;
  String url = "/switch?mac=" + macToStr(mac) + "&button=" + button;
  client.connect(bridgeIp, 80);
  client.print(String("GET ") + url + " HTTP/1.1\r\n" +
               "Host: " + bridgeIp + "\r\n" +
               "Connection: close\r\n\r\n");
}


void readButtons() {
  if (digitalRead(button1_pin) == HIGH) {
    button = 1;
  } else if (digitalRead(button2_pin) == HIGH) {
    button = 2;
  } else if (digitalRead(button3_pin) == HIGH) {
    button = 3;
  } else if (digitalRead(button4_pin) == HIGH) {
    button = 4;
  }
}


void blinkLed(uint8_t count) {
  for (uint8_t i = 0; i <= count; i++) {
    digitalWrite(2, LOW);
    delay(100);
    digitalWrite(2, HIGH);
    delay(100);
  }
}

void setup() {
  pinMode(button1_pin, INPUT);
  pinMode(button2_pin, INPUT);
  pinMode(button3_pin, INPUT);
  pinMode(button4_pin, INPUT);
  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);

  readButtons();


  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
  WiFi.macAddress(mac);

  while (WiFi.status() != WL_CONNECTED) {
    delay(50);
  }

  rst_info *rinfo;
  rinfo = ESP.getResetInfoPtr();

  if ((*rinfo).reason != REASON_DEEP_SLEEP_AWAKE) {

    WiFiClient client;
    client.connect(bridgeIp, 80);

    //register device
    String url = "/switch";
    url += "?devicetype=" + (String)switchType;
    url += "&mac=" + macToStr(mac);

    //###Registering device
    client.connect(bridgeIp, 80);
    client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                 "Host: " + bridgeIp + "\r\n" +
                 "Connection: close\r\n\r\n");
  }

}

void loop() {

  if (button == 1) {
    if (digitalRead(button4_pin) == HIGH) {
      ArduinoOTA.begin();
      blinkLed(5);
      otaEnabled = true;
      button = 5;
    } else {
      sendHttpRequest(1000);
    }
  }
  else if (button == 2) {
    sendHttpRequest(2000);
    delay(300);
    while (digitalRead(button2_pin) == HIGH) {
      delay(900);
      sendHttpRequest(2001);
    }
  }
  else if (button == 3) {
    sendHttpRequest(3000);
    delay(300);
    while (digitalRead(button3_pin) == HIGH) {
      delay(900);
      sendHttpRequest(3001);
    }
  }
  else if (button == 4) {
    sendHttpRequest(4000);
  }
  if (!otaEnabled || button != 5) {
    goingToSleep();
  }
  readButtons();
  ArduinoOTA.handle();
}
