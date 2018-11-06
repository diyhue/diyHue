#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

extern "C" {
#include "user_interface.h"
}

ADC_MODE(ADC_VCC);

#define button1_pin 4
#define button2_pin 3
#define button3_pin 13
#define button4_pin 14

#define shutdown_voltage 2.9 //depending on device, increase or decrease the value if the device don't enter in powersave mode when battery voltage is ~3.2v

const char* ssid = "WiFi name"; // replace with your wifi name
const char* password = "WiFi password"; // replace with your wifi password
const char* bridgeIp = "192.168.xxx.xxx"; //replace with the hue emulator device ip

//static ip configuration is necessary to minimize bootup time from deep sleep
IPAddress strip_ip ( 192,  168,   10,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   10,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);

// Existing firmware can be updated Over the Air (OTA) by enabling Arduino ota with ON and OFF buttons placed in same time (led will flash 5 times)

/// END USER CONFIG
const char* switchType = "ZLLSwitch";
bool otaEnabled = false;
uint32_t rtcData;



byte mac[6];
uint8_t button;

void goingToSleep(bool rfMode = true) {
  yield();
  delay(100);
  if (rfMode) {
    ESP.deepSleep(0, WAKE_RF_DEFAULT);
  } else {
    ESP.deepSleep(0, WAKE_RF_DISABLED);
  }
  yield();
  delay(100);
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
  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);
  ESP.rtcUserMemoryRead(0, &rtcData, sizeof(rtcData));
  if (rtcData == 1) {
    batteryMonitor();
  }
  pinMode(button1_pin, INPUT);
  pinMode(button2_pin, INPUT);
  pinMode(button3_pin, INPUT);
  pinMode(button4_pin, INPUT);


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
    batteryMonitor();
  }
  readButtons();
  ArduinoOTA.handle();
}
