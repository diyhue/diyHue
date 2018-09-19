#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h>
#include <EEPROM.h>


#define use_hardware_switch false // To control on/off state and brightness using GPIO/Pushbutton, set this value to true.
//For GPIO based on/off and brightness control, it is mandatory to connect the following GPIO pins to ground using 10k resistor
#define button1_pin 4 // on and brightness up
#define button2_pin 5 // off and brightness down

//define pins
#define LIGHTS_COUNT 4
uint8_t pins[LIGHTS_COUNT] = {12, 15, 13, 14};

//#define USE_STATIC_IP //! uncomment to enable Static IP Adress
#ifdef USE_STATIC_IP
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);
#endif

uint8_t scene;
bool light_state[LIGHTS_COUNT], in_transition;
int transitiontime[LIGHTS_COUNT], bri[LIGHTS_COUNT];
float step_level[LIGHTS_COUNT], current_bri[LIGHTS_COUNT];
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


void apply_scene(uint8_t new_scene,  uint8_t light) {
  if ( new_scene == 0) {
    bri[light] = 144;
  } else if ( new_scene == 1) {
    bri[light] = 254;
  } else if ( new_scene == 2) {
    bri[light] = 1;
  }
}

void process_lightdata(uint8_t light, float transitiontime) {
  transitiontime *= 16;
  if (light_state[light]) {
    step_level[light] = (bri[light] - current_bri[light]) / transitiontime;
  } else {
    step_level[light] = current_bri[light] / transitiontime;
  }
}


void lightEngine() {
  for (int i = 0; i < LIGHTS_COUNT; i++) {
    if (light_state[i]) {
      if (bri[i] != current_bri[i]) {
        in_transition = true;
        current_bri[i] += step_level[i];
        if ((step_level[i] > 0.0 && current_bri[i] > bri[i]) || (step_level[i] < 0.0 && current_bri[i] < bri[i])) {
          current_bri[i] = bri[i];
        }
        analogWrite(i, (int)(current_bri[i]));
      }
    } else {
      if (current_bri[i] != 0 ) {
        in_transition = true;
        current_bri[i] -= step_level[i];
        if (current_bri[i] < 0) {
          current_bri[i] = 0;
        }
        analogWrite(i, (int)(current_bri[i]));
      }
    }
  }
  if (in_transition) {
    delay(6);
    in_transition = false;
  } else if (use_hardware_switch == true) {
    if (digitalRead(button1_pin) == HIGH) {
      int i = 0;
      while (digitalRead(button1_pin) == HIGH && i < 30) {
        delay(20);
        i++;
      }
      for (int light = 0; light < LIGHTS_COUNT; light++) {
        if (i < 30) {
          // there was a short press
          light_state[light] = true;
        }
        else {
          // there was a long press
          bri[light] += 56;
          if (bri[light] > 254) {
            // don't increase the brightness more then maximum value
            bri[light] = 254;
          }
        }
        process_lightdata(light, 4);
      }
    } else if (digitalRead(button2_pin) == HIGH) {
      int i = 0;
      while (digitalRead(button2_pin) == HIGH && i < 30) {
        delay(20);
        i++;
      }
      for (int light = 0; light < LIGHTS_COUNT; light++) {
        if (i < 30) {
          // there was a short press
          light_state[light] = false;
        }
        else {
          // there was a long press
          bri[light] -= 56;
          if (bri[light] < 1) {
            // don't decrease the brightness less than minimum value.
            bri[light] = 1;
          }
        }
        process_lightdata(light, 4);
      }
    }
  }
}

void setup() {
  EEPROM.begin(512);
  
#ifdef USE_STATIC_IP
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
#endif

  analogWriteFreq(1000);
  analogWriteRange(255);

  for (uint8_t light = 0; light < LIGHTS_COUNT; light++) {
    apply_scene(EEPROM.read(2), light);
    step_level[light] = bri[light] / 150.0;
  }

  if (EEPROM.read(1) == 1 || (EEPROM.read(1) == 0 && EEPROM.read(0) == 1)) {
    for (int i = 0; i < LIGHTS_COUNT; i++) {
      light_state[i] = true;
    }
    for (int j = 0; j < 200; j++) {
      lightEngine();
    }
  }
  WiFiManager wifiManager;
  wifiManager.autoConnect("New Hue Light");
  if (! light_state[0])  {
    // Show that we are connected
    analogWrite(pins[1], 100);
    delay(500);
    analogWrite(pins[1], 0);
  }

  WiFi.macAddress(mac);

  // Port defaults to 8266
  // ArduinoOTA.setPort(8266);

  // Hostname defaults to esp8266-[ChipID]
  // ArduinoOTA.setHostname("myesp8266");

  // No authentication by default
  // ArduinoOTA.setPassword((const char *)"123");

  ArduinoOTA.begin();

  pinMode(LED_BUILTIN, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  digitalWrite(LED_BUILTIN, HIGH);  // Turn the LED off by making the voltage HIGH
  if (use_hardware_switch == true) {
    pinMode(button1_pin, INPUT);
    pinMode(button2_pin, INPUT);
  }


  server.on("/switch", []() {
    server.send(200, "text/plain", "OK");
    float transitiontime = 4;
    int button;
    for (uint8_t i = 0; i < server.args(); i++) {
      if (server.argName(i) == "button") {
        button = server.arg(i).toInt();
      }
    }
    for (int i = 0; i < LIGHTS_COUNT; i++) {
      if (button == 1000) {
        if (light_state[i] == false) {
          light_state[i] = true;
          scene = 0;
        } else {
          apply_scene(scene, i);
          scene++;
          if (scene == 11) {
            scene = 0;
          }
        }
      } else if (button == 2000) {
        if (light_state[i] == false) {
          bri[i] = 30;
          light_state[i] = true;
        } else {
          bri[i] += 30;
        }
        if (bri[i] > 255) bri[i] = 255;
      } else if (button == 3000 && light_state[i] == true) {
        bri[i] -= 30;
        if (bri[i] < 1) bri[i] = 1;
      } else if (button == 4000) {
        light_state[i] = false;
      }
      if (light_state[i]) {
        step_level[i] = ((float)bri[i] - current_bri[i]) / transitiontime;
      } else {
        step_level[i] = current_bri[i] / transitiontime;
      }
    }
  });

  server.on("/set", []() {
    uint8_t light;
    float transitiontime = 4;
    for (uint8_t i = 0; i < server.args(); i++) {
      if (server.argName(i) == "light") {
        light = server.arg(i).toInt() - 1;
      }
      else if (server.argName(i) == "on") {
        if (server.arg(i) == "True" || server.arg(i) == "true") {
          light_state[light] = true;
          if (EEPROM.read(1) == 0 && EEPROM.read(0) == 0) {
            EEPROM.write(0, 1);
          }
        }
        else {
          light_state[light] = false;
          if (EEPROM.read(1) == 0 && EEPROM.read(0) == 1) {
            EEPROM.write(0, 0);
          }
        }
        EEPROM.commit();
      }
      else if (server.argName(i) == "bri") {
        light_state[light] = true;
        if (server.arg(i).toInt() != 0)
          bri[light] = server.arg(i).toInt();
      }
      else if (server.argName(i) == "bri_inc") {
        bri[light] += server.arg(i).toInt();
        if (bri[light] > 255) bri[light] = 255;
        else if (bri[light] < 0) bri[light] = 0;
      }
      else if (server.argName(i) == "alert" && server.arg(i) == "select") {
        if (light_state[light]) {
          current_bri[light] = 0;
        } else {
          current_bri[light] = 255;
        }
      }
      else if (server.argName(i) == "transitiontime") {
        transitiontime = server.arg(i).toInt();
      }
    }
    process_lightdata(light, transitiontime);
    server.send(200, "text/plain", "OK, bri:" + (String)bri[light] + ", state:" + light_state[light]);
  });

  server.on("/get", []() {
    uint8_t light;
    if (server.hasArg("light"))
      light = server.arg("light").toInt() - 1;
    String power_status;
    power_status = light_state[light] ? "true" : "false";
    server.send(200, "text/plain", "{\"on\": " + power_status + ", \"bri\": " + (String)bri[light] + "}");
  });

  server.on("/detect", []() {
    server.send(200, "text/plain", "{\"hue\": \"bulb\",\"lights\": " + (String)LIGHTS_COUNT + ",\"modelid\": \"LWB010\",\"mac\": \"" + String(mac[5], HEX) + ":"  + String(mac[4], HEX) + ":" + String(mac[3], HEX) + ":" + String(mac[2], HEX) + ":" + String(mac[1], HEX) + ":" + String(mac[0], HEX) + "\"}");
  });

  server.on("/", []() {
    float transitiontime = 4;
    if (server.hasArg("startup")) {
      if (  EEPROM.read(1) != server.arg("startup").toInt()) {
        EEPROM.write(1, server.arg("startup").toInt());
        EEPROM.commit();
      }
    }

    for (int light = 0; light < LIGHTS_COUNT; light++) {
      if (server.hasArg("scene")) {
        if (server.arg("bri") == "" && server.arg("hue") == "" && server.arg("ct") == "" && server.arg("sat") == "") {
          if (  EEPROM.read(2) != server.arg("scene").toInt()) {
            EEPROM.write(2, server.arg("scene").toInt());
            EEPROM.commit();
          }
          apply_scene(server.arg("scene").toInt(), light);
        } else {
          if (server.arg("bri") != "") {
            bri[light] = server.arg("bri").toInt();
          }
        }
      } else if (server.hasArg("on")) {
        if (server.arg("on") == "true") {
          light_state[light] = true; {
            if (EEPROM.read(1) == 0 && EEPROM.read(0) == 0) {
              EEPROM.write(0, 1);
            }
          }
        } else {
          light_state[light] = false;
          if (EEPROM.read(1) == 0 && EEPROM.read(0) == 1) {
            EEPROM.write(0, 0);
          }
        }
        EEPROM.commit();
      } else if (server.hasArg("alert")) {
        if (light_state[light]) {
          current_bri[light] = 0;
        } else {
          current_bri[light] = 255;
        }
      }
      if (light_state[light]) {
        step_level[light] = ((float)bri[light] - current_bri[light]) / transitiontime;
      } else {
        step_level[light] = current_bri[light] / transitiontime;
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
    http_content += "<a class=\"pure-button"; if (light_state[0]) http_content += "  pure-button-primary"; http_content += "\" href=\"/?on=true\">ON</a>";
    http_content += "<a class=\"pure-button"; if (!light_state[0]) http_content += "  pure-button-primary"; http_content += "\" href=\"/?on=false\">OFF</a>";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"startup\">Startup</label>";
    http_content += "<select onchange=\"this.form.submit()\" id=\"startup\" name=\"startup\">";
    http_content += "<option "; if (EEPROM.read(1) == 0) http_content += "selected=\"selected\""; http_content += " value=\"0\">Last state</option>";
    http_content += "<option "; if (EEPROM.read(1) == 1) http_content += "selected=\"selected\""; http_content += " value=\"1\">On</option>";
    http_content += "<option "; if (EEPROM.read(1) == 2) http_content += "selected=\"selected\""; http_content += " value=\"2\">Off</option>";
    http_content += "</select>";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"scene\">Scene</label>";
    http_content += "<select onchange = \"this.form.submit()\" id=\"scene\" name=\"scene\">";
    http_content += "<option "; if (EEPROM.read(2) == 0) http_content += "selected=\"selected\""; http_content += " value=\"0\">Relax</option>";
    http_content += "<option "; if (EEPROM.read(2) == 1) http_content += "selected=\"selected\""; http_content += " value=\"1\">Bright</option>";
    http_content += "<option "; if (EEPROM.read(2) == 2) http_content += "selected=\"selected\""; http_content += " value=\"2\">Nightly</option>";
    http_content += "</select>";
    http_content += "</div>";
    http_content += "<br>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"state\"><strong>State</strong></label>";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"bri\">Bri</label>";
    http_content += "<input id=\"bri\" name=\"bri\" type=\"text\" placeholder=\"" + (String)bri[0] + "\">";
    http_content += "</div>";

    http_content += "<div class=\"pure-controls\">";
    http_content += "<span class=\"pure-form-message\"><a href=\"/?alert=1\">alert</a> or <a href=\"/?reset=1\">reset</a></span>";
    http_content += "<label for=\"cb\" class=\"pure-checkbox\">";
    http_content += "</label>";
    http_content += "<button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button>";
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
  lightEngine();
}
