#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

extern "C" {
#include "gpio.h"
#include "user_interface.h"
}

#define button1_pin 1
#define button2_pin 3
#define button3_pin 5
#define button4_pin 4

const char* ssid = "MikroTik";
const char* password = "nustiuceparola";
const char* switchType = "ZLLSwitch";
const char* bridge_user = "9f552609847c0dd1f372fee9b76330035b7a3bb1";

//Set bridge ip or ip of every light controlled by this switch
const char* bridgeIp[] = {"192.168.10.200"};

//static ip configuration is necessary to minimize bootup time from deep sleep
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
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

void sendHttpRequest(int button) {
  WiFiClient client;
  for (int i = 0; i < sizeof(bridgeIp) / 4; i++) {
    String url = "/switch?mac=" + macToStr(mac) + "&button=" + button;
    client.connect(bridgeIp[i], 80);
    client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                 "Host: " + bridgeIp[0] + "\r\n" +
                 "Connection: close\r\n\r\n");
  }
}

void setup() {
  pinMode(16, OUTPUT);
  pinMode(button1_pin, INPUT);
  pinMode(button2_pin, INPUT);
  pinMode(button3_pin, INPUT);
  pinMode(button4_pin, INPUT);
  digitalWrite(button1_pin, LOW);
  digitalWrite(button2_pin, LOW);
  digitalWrite(button3_pin, LOW);
  digitalWrite(button4_pin, LOW);
  digitalWrite(16, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
  WiFi.macAddress(mac);

  while (WiFi.status() != WL_CONNECTED) {
    delay(50);
  }

  ArduinoOTA.begin();

  rst_info *rinfo;
  rinfo = ESP.getResetInfoPtr();

  if ((*rinfo).reason != REASON_DEEP_SLEEP_AWAKE) {

    WiFiClient client;
    client.connect(bridgeIp[0], 80);

    //register device
    String url = "/switch";
    url += "?devicetype=" + (String)switchType;
    url += "&mac=" + macToStr(mac);

    //###Registering device
    client.connect(bridgeIp[0], 80);
    client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                 "Host: " + bridgeIp[0] + "\r\n" +
                 "Connection: close\r\n\r\n");
  }

}

void loop() {
  ArduinoOTA.handle();
  delay(1);

  if (digitalRead(button1_pin) == HIGH) {
    sendHttpRequest(1000);
    counter = 0;
    int i = 0;
    while (digitalRead(button1_pin) == HIGH && i < 30) {
      delay(20);
      i++;
    }
  }
  if (digitalRead(button2_pin) == HIGH) {
    counter = 0;
    int i = 0;
    while (digitalRead(button2_pin) == HIGH && i < 30) {
      delay(20);
      i++;
    }
    if (i < 30) {
      sendHttpRequest(2000);
    } else {
      sendHttpRequest(2001);
    }
  }
  if (digitalRead(button3_pin) == HIGH) {
    counter = 0;
    int i = 0;
    while (digitalRead(button3_pin) == HIGH && i < 30) {
      delay(20);
      i++;
    }
    if (i < 30) {
      sendHttpRequest(3000);
    } else {
      sendHttpRequest(3001);
    }
  }
  if (digitalRead(button4_pin) == HIGH) {
    sendHttpRequest(4000);
    counter = 0;
    int i = 0;
    while (digitalRead(button4_pin) == HIGH && i < 30) {
      delay(20);
      i++;
    }
  }
  if (counter == 5000) {
    goingToSleep();
  } else {
    counter++;
  }
}
