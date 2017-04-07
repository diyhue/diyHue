#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ESP8266WebServer.h>

extern "C" {
#include "gpio.h"
}
extern "C" {
#include "user_interface.h"
}

const char* ssid = "OT Office";
const char* password = "Otopeni!";
const char* host = "192.168.0.22";
const int httpPort = 81;
int counter;
byte mac[6];
IPAddress strip_ip ( 192,  168,   0,  95);
IPAddress gateway_ip ( 192,  168,   0,   1);
IPAddress subnet_mask(255, 255, 255,   0);
WiFiClient client;
ESP8266WebServer server(80);

void handleNotFound() {
  String message = "File Not Found\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  for (uint8_t i = 0; i < server.args(); i++) {
    message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
  }
  server.send(404, "text/plain", message);
}

void setup() {
  //Serial.begin(115200);
  //Serial.print("initializing GPIOs");
  gpio_init();
  pinMode(0, INPUT); // this pin is connected to the PIR sensor.
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  WiFi.config(strip_ip, gateway_ip, subnet_mask);

  WiFi.macAddress(mac);

  server.on("/detect", []() {
    server.send(200, "text/plain", "{\"hue\":\"sensor\", \"type\":\"tap\", \"mac\":\"" + String(mac[5], HEX) + ":"  + String(mac[3], HEX) + ":" + String(mac[3], HEX) + ":" + String(mac[2], HEX) + ":" + String(mac[1], HEX) + ":" + String(mac[0], HEX) + "\"}");
  });

  server.onNotFound(handleNotFound);

  server.begin();
}

void loop() {
  delay(2);
  server.handleClient();
  if (counter > 10000) {
    sleepNow();
  }
  if (counter == 0)
    sendHttpRequest();
  counter++;
}

void sleepNow() {
  //Serial.println("going to light sleep...");
  wifi_station_disconnect();
  wifi_set_opmode(NULL_MODE);
  wifi_fpm_set_sleep_type(LIGHT_SLEEP_T); //light sleep mode
  gpio_pin_wakeup_enable(GPIO_ID_PIN(2), GPIO_PIN_INTR_LOLEVEL); //set the interrupt to look for HIGH pulses on Pin 0 (the PIR).
  wifi_fpm_open();
  delay(100);
  wifi_fpm_set_wakeup_cb(wakeupFromMotion); //wakeup callback
  wifi_fpm_do_sleep(0xFFFFFFF);
  delay(100);
}

void wakeupFromMotion(void) {
  wifi_fpm_close;
  wifi_set_opmode(STATION_MODE);
  wifi_station_connect();
  //Serial.println("Woke up from sleep");
  counter = 0;
}

void sendHttpRequest() {
  //Serial.println("Wait for wi-fi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(50);
  }
  //Serial.println("Send request...");
  client.connect(host, 80);
  client.print("HTTP/1.1\r\n");
  //Serial.println("Done!");
}

