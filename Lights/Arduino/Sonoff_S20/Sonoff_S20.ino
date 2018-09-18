#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h>
#include <EEPROM.h>

#define devicesCount 1

uint8_t devicesPins[devicesCount] = {12};
uint8_t ledPin = 13;

const uint8_t buttonPin = 0;    // the pin that the pushbutton is attached to
uint8_t buttonState = digitalRead(buttonPin);
uint8_t lastButtonState = buttonState;
unsigned long lastButtonPush = 0;
uint8_t buttonThreshold = 50;

//#define USE_STATIC_IP //! uncomment to enable Static IP Adress
#ifdef USE_STATIC_IP
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);
#endif

bool device_state[devicesCount];
byte mac[6];

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
  EEPROM.begin(512);

  for (uint8_t ch = 0; ch < devicesCount; ch++) {
    pinMode(devicesPins[ch], OUTPUT);
  }

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);
  
#ifdef USE_STATIC_IP
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
#endif

  if (EEPROM.read(1) == 1 || (EEPROM.read(1) == 0 && EEPROM.read(0) == 1)) {
    for (uint8_t i = 0; i < devicesCount; i++) {
      digitalWrite(devicesPins[i], OUTPUT);
      device_state[i] = true;
    }
  }

  WiFiManager wifiManager;
  wifiManager.autoConnect("New Hue Plug");

  if (!device_state[0]) {
    while (WiFi.status() != WL_CONNECTED) {
      // Blink the button led
      digitalWrite(ledPin, HIGH);
      delay(100);
      digitalWrite(ledPin, LOW);
      delay(100);
    }
  }
  // OK
  digitalWrite(ledPin, LOW);
  delay(1000);
  digitalWrite(ledPin, HIGH);

  WiFi.macAddress(mac);

  // Port defaults to 8266
  // ArduinoOTA.setPort(8266);

  // Hostname defaults to esp8266-[ChipID]
  //ArduinoOTA.setHostname("HuePlugTwo");

  // No authentication by default
  //ArduinoOTA.setPassword((const char *)"123");

  ArduinoOTA.begin();

  server.on("/set", []() {
    uint8_t device;

    for (uint8_t i = 0; i < server.args(); i++) {
      if (server.argName(i) == "light") {
        device = server.arg(i).toInt() - 1;
      }
      else if (server.argName(i) == "on") {
        if (server.arg(i) == "True" || server.arg(i) == "true") {
          if (EEPROM.read(1) == 0 && EEPROM.read(0) != 1) {
            EEPROM.write(0, 1);
            EEPROM.commit();
          }
          device_state[device] = true;
          digitalWrite(devicesPins[device], HIGH);
        }
        else {
          if (EEPROM.read(1) == 0 && EEPROM.read(0) != 0) {
            EEPROM.write(0, 0);
            EEPROM.commit();
          }
          device_state[device] = false;
          digitalWrite(devicesPins[device], LOW);
        }
      }
    }
    server.send(200, "text/plain", "OK, state:" + device_state[device]);
  });

  server.on("/get", []() {
    uint8_t light;
    if (server.hasArg("light"))
      light = server.arg("light").toInt() - 1;
    String power_status;
    power_status = device_state[light] ? "true" : "false";
    server.send(200, "text/plain", "{\"on\": " + power_status + "}");
  });

  server.on("/detect", []() {
    server.send(200, "text/plain", "{\"hue\": \"bulb\",\"lights\": " + String(devicesCount) + ",\"modelid\": \"Plug 01\",\"mac\": \"" + String(mac[5], HEX) + ":"  + String(mac[4], HEX) + ":" + String(mac[3], HEX) + ":" + String(mac[2], HEX) + ":" + String(mac[1], HEX) + ":" + String(mac[0], HEX) + "\"}");
  });

  server.on("/", []() {
    float transitiontime = 100;
    if (server.hasArg("startup")) {
      if (  EEPROM.read(1) != server.arg("startup").toInt()) {
        EEPROM.write(1, server.arg("startup").toInt());
        EEPROM.commit();
      }
    }

    for (uint8_t device = 0; device < devicesCount; device++) {

      if (server.hasArg("on")) {
        if (server.arg("on") == "true") {
          device_state[device] = true;
          digitalWrite(devicesPins[device], HIGH);
          if (EEPROM.read(1) == 0 && EEPROM.read(0) != 1) {
            EEPROM.write(0, 1);
            EEPROM.commit();
          }
        } else {
          device_state[device] = false;
          digitalWrite(devicesPins[device], LOW);
          if (EEPROM.read(1) == 0 && EEPROM.read(0) != 0) {
            EEPROM.write(0, 0);
            EEPROM.commit();
          }
        }
      }
    }
    if (server.hasArg("reset")) {
      ESP.reset();
    }


    String http_content = "<!doctype html>";
    http_content += "<html>";
    http_content += "<head>";
    http_content += "<meta charset=\"utf-8\">";
    http_content += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">";
    http_content += "<title>Light Setup</title>";
    http_content += "<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">";
    http_content += "</head>";
    http_content += "<body>";
    http_content += "<fieldset>";
    http_content += "<h3>Light Setup</h3>";
    http_content += "<form class=\"pure-form pure-form-aligned\" action=\"/\" method=\"post\">";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"power\"><strong>Power</strong></label>";
    http_content += "<a class=\"pure-button"; if (device_state[0]) http_content += "  pure-button-primary"; http_content += "\" href=\"/?on=true\">ON</a>";
    http_content += "<a class=\"pure-button"; if (!device_state[0]) http_content += "  pure-button-primary"; http_content += "\" href=\"/?on=false\">OFF</a>";
    http_content += "</div>";
    http_content += "</fieldset>";
    http_content += "</form>";
    http_content += "</body>";
    http_content += "</html>";

    server.send(200, "text/html", http_content);

  });


  server.onNotFound(handleNotFound);

  server.begin();
}

void loop() {
  ArduinoOTA.handle();
  server.handleClient();

  if (millis() < lastButtonPush + buttonThreshold) return; // check button only when the threshold after last push is reached

  lastButtonPush = millis();

  buttonState = digitalRead(buttonPin);

  // compare the buttonState to its previous state
  if (buttonState == lastButtonState) return;

  if (buttonState == HIGH) {
    for (uint8_t device = 0; device < devicesCount; device++) {
      device_state[device] = !device_state[device];

      if (device_state[device] == true) {
        digitalWrite(devicesPins[device], HIGH);
        if (EEPROM.read(1) == 0 && EEPROM.read(0) != 1) {
          EEPROM.write(0, 1);
          EEPROM.commit();
        }
      } else {
        digitalWrite(devicesPins[device], LOW);
        if (EEPROM.read(1) == 0 && EEPROM.read(0) != 0) {
          EEPROM.write(0, 0);
          EEPROM.commit();
        }
      }
    }
  }

  // save the current state as the last state, for next time through the loop
  lastButtonState = buttonState;

}
