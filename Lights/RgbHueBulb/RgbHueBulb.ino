#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <ESP8266WebServer.h>


const char* ssid = "MikroTik";
const char* password = "nustiuceparola";

#define red_pin 16
#define green_pin 4
#define blue_pin 5
#define startup_brightness 250
#define startup_color 0
// 0 = warm_white, 1 =  neutral, 2 = cold_white, 3 = red, 4 = green, 5 = blue

// if you want to setup static ip uncomment these 3 lines and line 69
//IPAddress strip_ip ( 192,  168,   10,  95);
//IPAddress gateway_ip ( 192,  168,   10,   1);
//IPAddress subnet_mask(255, 255, 255,   0);

uint8_t rgb[3];
bool light_state, level[3];
int fade;
float step_level[3], current_rgb[3];
byte mac[6];

ESP8266WebServer server(80);


int getArgValue(String name)
{
  for (uint8_t i = 0; i < server.args(); i++)
    if (server.argName(i) == name)
      return server.arg(i).toInt();
  return -1;
}

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
  analogWriteRange(255);
  analogWrite(red_pin, 0);
  analogWrite(green_pin, 0);
  analogWrite(blue_pin, 0);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  //WiFi.config(strip_ip, gateway_ip, subnet_mask);

  if (startup_brightness == 0) {
    analogWrite(red_pin, 255);
    analogWrite(green_pin, 255);
    analogWrite(blue_pin, 255);
    delay(200);
    analogWrite(red_pin, 0);
    analogWrite(green_pin, 0);
    analogWrite(blue_pin, 0);


    while (WiFi.status() != WL_CONNECTED) {
      analogWrite(red_pin, 255);
      delay(250);
      analogWrite(red_pin, 0);
      delay(250);
    }
    // Show that we are connected
    analogWrite(green_pin, 255);
    delay(500);
    analogWrite(green_pin, 0);
    //setup default warm_white on power on
    rgb[0] = 254; rgb[1] = 145; rgb[2] = 40;

  } else {
    //setup start color/brightness and fade
    if ( startup_color == 0) {
      rgb[0] = (int) 254 * (startup_brightness / 255.0f); rgb[1] = (int) 145 * (startup_brightness / 255.0f); rgb[2] = (int) 40 * (startup_brightness / 255.0f);
    } else if ( startup_color == 1) {
      rgb[0] = 254 * (startup_brightness / 255.0f); rgb[1] = 177 * (startup_brightness / 255.0f); rgb[2] = 111 * (startup_brightness / 255.0f);
    } else if ( startup_color == 2) {
      rgb[0] = 254 * (startup_brightness / 255.0f); rgb[1] = 233 * (startup_brightness / 255.0f); rgb[2] = 216 * (startup_brightness / 255.0f);
    }  else if ( startup_color == 3) {
      rgb[0] = 254 * (startup_brightness / 255.0f); rgb[1] = 0; rgb[2] = 0;
    }  else if ( startup_color == 4) {
      rgb[0] = 0; rgb[1] = 254 * (startup_brightness / 255.0f); rgb[2] = 0;
    }  else if ( startup_color == 5) {
      rgb[0] = 0; rgb[1] = 0; rgb[2] = 254 * (startup_brightness / 255.0f);
    }
    step_level[0] = rgb[0] / 100.0f; step_level[1] = rgb[1] / 100.0f; step_level[2] = rgb[2] / 100.0f;
    level[0] = true; level[1] = true; level[2] = true;
    light_state = true;
  }

  WiFi.macAddress(mac);

  // Port defaults to 8266
  // ArduinoOTA.setPort(8266);

  // Hostname defaults to esp8266-[ChipID]
  // ArduinoOTA.setHostname("myesp8266");

  // No authentication by default
  // ArduinoOTA.setPassword((const char *)"123");

  ArduinoOTA.onStart([]() {
    Serial.println("Start");
  });
  ArduinoOTA.onEnd([]() {
    Serial.println("\nEnd");
  });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("Error[%u]: ", error);
    if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
    else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
    else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
    else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
    else if (error == OTA_END_ERROR) Serial.println("End Failed");
  });
  ArduinoOTA.begin();

  pinMode(LED_BUILTIN, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  digitalWrite(LED_BUILTIN, HIGH);  // Turn the LED off by making the voltage HIGH


  server.on("/set", []() {
    rgb[0] = getArgValue("r");
    rgb[1] = getArgValue("g");
    rgb[2] = getArgValue("b");
    fade = getArgValue("fade");
    if (fade == -1) fade = 400;
    server.send(200, "text/plain", "OK, R:" + (String)rgb[0] + " ,B:" + (String)rgb[1] + " ,G:" + (String)rgb[2]);
    step_level[0] = (rgb[0] - current_rgb[0]) / (fade / 2);
    step_level[1] = (rgb[1] - current_rgb[1]) / (fade / 2);
    step_level[2] = (rgb[2] - current_rgb[2]) / (fade / 2);
    rgb[0] > current_rgb[0] ? level[0] = true : level[0] = false;
    rgb[1] > current_rgb[1] ? level[1] = true : level[1] = false;
    rgb[2] > current_rgb[2] ? level[2] = true : level[2] = false;
    light_state = true;
  });

  server.on("/off", []() {
    fade = getArgValue("fade");
    if (fade == -1) fade = 150;
    server.send(200, "text/plain", "OK");
    step_level[0] = current_rgb[0] / (fade / 1.5);
    step_level[1] = current_rgb[1] / (fade / 1.5);
    step_level[2] = current_rgb[2] / (fade / 1.5);
    light_state = false;

  });

  server.on("/on", []() {
    fade = getArgValue("fade");
    if (fade == -1) fade = 150;
    server.send(200, "text/plain", "OK");
    step_level[0] = rgb[0] / (fade / 1.5);
    step_level[1] = rgb[1] / (fade / 1.5);
    step_level[2] = rgb[2] / (fade / 1.5);
    level[0] = true;
    level[1] = true;
    level[2] = true;
    light_state = true;
  });

  server.on("/detect", []() {
    server.send(200, "text/plain", "{\"hue\": \"bulb\",\"lights\": 1,\"type\": \"rgbw\",\"mac\": \"" + String(mac[5], HEX) + ":"  + String(mac[4], HEX) + ":" + String(mac[3], HEX) + ":" + String(mac[2], HEX) + ":" + String(mac[1], HEX) + ":" + String(mac[0], HEX) + "\"}");
  });


  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  ArduinoOTA.handle();
  server.handleClient();
  lightEngine();
}


void lightEngine() {
  int white_level = 255;
  if (light_state) {
    if (rgb[0] != (int)current_rgb[0] || rgb[1] != (int)current_rgb[1] || rgb[2] != (int)current_rgb[2]) {
      if (rgb[0] != (int)current_rgb[0]) current_rgb[0] += step_level[0];
      if (rgb[1] != (int)current_rgb[1]) current_rgb[1] += step_level[1];
      if (rgb[2] != (int)current_rgb[2]) current_rgb[2] += step_level[2];
      if (level[0] && current_rgb[0] > rgb[0]) current_rgb[0] = rgb[0];
      if (level[1] && current_rgb[1] > rgb[1]) current_rgb[1] = rgb[1];
      if (level[2] && current_rgb[2] > rgb[2]) current_rgb[2] = rgb[2];
      if (!level[0] && current_rgb[0] < rgb[0]) current_rgb[0] = rgb[0];
      if (!level[1] && current_rgb[1] < rgb[1]) current_rgb[1] = rgb[1];
      if (!level[2] && current_rgb[2] < rgb[2]) current_rgb[2] = rgb[2];
      analogWrite(red_pin, current_rgb[0]);
      analogWrite(green_pin, current_rgb[1]);
      analogWrite(blue_pin, current_rgb[2]);
    }
  } else {
    if ((int)current_rgb[0] != 0 || (int)current_rgb[1] != 0 || (int)current_rgb[2] != 0) {
      if ((int)current_rgb[0] != 0) current_rgb[0] -= step_level[0];
      if ((int)current_rgb[1] != 0) current_rgb[1] -= step_level[1];
      if ((int)current_rgb[2] != 0) current_rgb[2] -= step_level[2];
      if ((int)current_rgb[0] < 0) current_rgb[0] = 0;
      if ((int)current_rgb[1] < 0) current_rgb[1] = 0;
      if ((int)current_rgb[2] < 0) current_rgb[2] = 0;
      analogWrite(red_pin, current_rgb[0]);
      analogWrite(green_pin, current_rgb[1]);
      analogWrite(blue_pin, current_rgb[2]);
    }
  }
  delay(2);
}
