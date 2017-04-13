#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <ESP8266WebServer.h>
#include <math.h>


const char* ssid = "MikroTik";
const char* password = "nustiuceparola";

#define red_pin 12
#define green_pin 13
#define blue_pin 14
#define white_pin 5
#define startup_brightness 250
#define startup_color 0
// 0 = warm_white, 1 = neutral, 2 = cold_white, 3 = red, 4 = green, 5 = blue

// if you want to setup static ip uncomment these 3 lines and line 69
//IPAddress strip_ip ( 192,  168,   10,  95);
//IPAddress gateway_ip ( 192,  168,   10,   1);
//IPAddress subnet_mask(255, 255, 255,   0);

uint8_t rgb[3], color_mode = 2;
bool light_state;
int transitiontime, ct = 400, hue, bri = 250, sat;
float step_level[3], current_rgb[3], x, y;
byte mac[6];

ESP8266WebServer server(80);

void convert_hue()
{
  double      hh, p, q, t, ff, s, v;
  long        i;

  s = sat / 255.0;
  v = bri / 255.0;

  if (s <= 0.0) {      // < is bogus, just shuts up warnings
    rgb[0] = v;
    rgb[1] = v;
    rgb[2] = v;
    return;
  }
  hh = hue;
  if (hh >= 65535.0) hh = 0.0;
  hh /= 11850, 0;
  i = (long)hh;
  ff = hh - i;
  p = v * (1.0 - s);
  q = v * (1.0 - (s * ff));
  t = v * (1.0 - (s * (1.0 - ff)));

  switch (i) {
    case 0:
      rgb[0] = v * 255.0;
      rgb[1] = t * 255.0;
      rgb[2] = p * 255.0;
      break;
    case 1:
      rgb[0] = q * 255.0;
      rgb[1] = v * 255.0;
      rgb[2] = p * 255.0;
      break;
    case 2:
      rgb[0] = p * 255.0;
      rgb[1] = v * 255.0;
      rgb[2] = t * 255.0;
      break;

    case 3:
      rgb[0] = p * 255.0;
      rgb[1] = q * 255.0;
      rgb[2] = v * 255.0;
      break;
    case 4:
      rgb[0] = t * 255.0;
      rgb[1] = p * 255.0;
      rgb[2] = v * 255.0;
      break;
    case 5:
    default:
      rgb[0] = v * 255.0;
      rgb[1] = p * 255.0;
      rgb[2] = q * 255.0;
      break;
  }

}

void convert_xy()
{
  float Y = bri / 250.0f;

  float z = 1.0f - x - y;

  float X = (Y / y) * x;
  float Z = (Y / y) * z;

  // sRGB D65 conversion
  float r =  X * 1.656492f - Y * 0.354851f - Z * 0.255038f;
  float g = -X * 0.707196f + Y * 1.655397f + Z * 0.036152f;
  float b =  X * 0.051713f - Y * 0.121364f + Z * 1.011530f;

  if (r > b && r > g && r > 1.0f) {
    // red is too big
    g = g / r;
    b = b / r;
    r = 1.0f;
  }
  else if (g > b && g > r && g > 1.0f) {
    // green is too big
    r = r / g;
    b = b / g;
    g = 1.0f;
  }
  else if (b > r && b > g && b > 1.0f) {
    // blue is too big
    r = r / b;
    g = g / b;
    b = 1.0f;
  }

  // Apply gamma correction
  r = r <= 0.0031308f ? 12.92f * r : (1.0f + 0.055f) * pow(r, (1.0f / 2.4f)) - 0.055f;
  g = g <= 0.0031308f ? 12.92f * g : (1.0f + 0.055f) * pow(g, (1.0f / 2.4f)) - 0.055f;
  b = b <= 0.0031308f ? 12.92f * b : (1.0f + 0.055f) * pow(b, (1.0f / 2.4f)) - 0.055f;

  if (r > b && r > g) {
    // red is biggest
    if (r > 1.0f) {
      g = g / r;
      b = b / r;
      r = 1.0f;
    }
  }
  else if (g > b && g > r) {
    // green is biggest
    if (g > 1.0f) {
      r = r / g;
      b = b / g;
      g = 1.0f;
    }
  }
  else if (b > r && b > g) {
    // blue is biggest
    if (b > 1.0f) {
      r = r / b;
      g = g / b;
      b = 1.0f;
    }
  }

  r = r < 0 ? 0 : r;
  g = g < 0 ? 0 : g;
  b = b < 0 ? 0 : b;

  rgb[0] = (int) (r * 255.0f); rgb[1] = (int) (g * 255.0f); rgb[2] = (int) (b * 255.0f);
}

void convert_ct() {
  int hectemp = 10000 / ct;
  int r, g, b;
  if (hectemp <= 66) {
    r = 255;
    g = 99.4708025861 * log(hectemp) - 161.1195681661;
    b = hectemp <= 19 ? 0 : (138.5177312231 * log(hectemp - 10) - 305.0447927307);
  } else {
    r = 329.698727446 * pow(hectemp - 60, -0.1332047592);
    g = 288.1221695283 * pow(hectemp - 60, -0.0755148492);
    b = 255;
  }
  r = r > 255 ? 255 : r;
  g = g > 255 ? 255 : g;
  b = b > 255 ? 255 : b;
  rgb[0] = r * (bri / 255.0f); rgb[1] = g * (bri / 255.0f); rgb[2] = b * (bri / 255.0f);
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
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  //analogWriteRange(255);
  delay(500);
  analogWrite(red_pin, 0);
  analogWrite(green_pin, 0);
  analogWrite(blue_pin, 0);
  analogWrite(white_pin, 0);

  //WiFi.config(strip_ip, gateway_ip, subnet_mask);

  if (startup_brightness == 0) {

    while (WiFi.status() != WL_CONNECTED) {
      analogWrite(red_pin, 10);
      delay(250);
      analogWrite(red_pin, 0);
      delay(250);
    }
    // Show that we are connected
    analogWrite(green_pin, 10);
    delay(500);
    analogWrite(green_pin, 0);
    //setup default warm_white on power on
    convert_ct();

  } else {
    bri = startup_brightness;
    //setup start color/brightness and transitiontime
    if ( startup_color == 0) {
      ct = 400; convert_ct();
    } else if ( startup_color == 1) {
      ct = 320; convert_ct();
    } else if ( startup_color == 2) {
      ct = 200; convert_ct();
    }  else if ( startup_color == 3) {
      rgb[0] = 254 * (startup_brightness / 255.0f); rgb[1] = 0; rgb[2] = 0;
    }  else if ( startup_color == 4) {
      rgb[0] = 0; rgb[1] = 254 * (startup_brightness / 255.0f); rgb[2] = 0;
    }  else if ( startup_color == 5) {
      rgb[0] = 0; rgb[1] = 0; rgb[2] = 254 * (startup_brightness / 255.0f);
    }
    step_level[0] = rgb[0] / 350.0f; step_level[1] = rgb[1] / 350.0f; step_level[2] = rgb[2] / 350.0f;
    light_state = true;
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


  server.on("/set", []() {
    light_state = true;
    float transitiontime = 40;
    for (uint8_t i = 0; i < server.args(); i++) {
      if (server.argName(i) == "on") {
        if (server.arg(i) == "1") {
          light_state = true;
        }
        else {
          light_state = false;
        }
      }
      else if (server.argName(i) == "r") {
        rgb[0] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "g") {
        rgb[1] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "b") {
        rgb[2] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "x") {
        x = server.arg(i).toFloat();
        color_mode = 1;
      }
      else if (server.argName(i) == "y") {
        y = server.arg(i).toFloat();
        color_mode = 1;
      }
      else if (server.argName(i) == "bri") {
        if (server.arg(i).toInt() == 0)
          light_state = true;
        else
          bri = server.arg(i).toInt();
      }
      else if (server.argName(i) == "bri_inc") {
        bri += server.arg(i).toInt();
        if (bri > 255) bri = 255;
        else if (bri < 0) bri = 0;
      }
      else if (server.argName(i) == "ct") {
        ct = server.arg(i).toInt();
        color_mode = 2;
      }
      else if (server.argName(i) == "sat") {
        sat = server.arg(i).toInt();
        color_mode = 3;
      }
      else if (server.argName(i) == "hue") {
        hue = server.arg(i).toInt();
        color_mode = 3;
      }
      else if (server.argName(i) == "transitiontime") {
        transitiontime = server.arg(i).toInt() * 60;
      }
    }
    server.send(200, "text/plain", "OK, x: " + (String)x + ", y:" + (String)y + ", bri:" + (String)bri + ", ct:" + ct + ", colormode:" + color_mode + ", state:" + light_state);
    if (color_mode == 1 && light_state == true) {
      convert_xy();
    } else if (color_mode == 2 && light_state == true) {
      convert_ct();
    } else if (color_mode == 3 && light_state == true) {
      convert_hue();
    }
    if (light_state) {
      step_level[0] = (rgb[0] - current_rgb[0]) / transitiontime;
      step_level[1] = (rgb[1] - current_rgb[1]) / transitiontime;
      step_level[2] = (rgb[2] - current_rgb[2]) / transitiontime;
    } else {
      step_level[0] = current_rgb[0] / transitiontime;
      step_level[1] = current_rgb[1] / transitiontime;
      step_level[2] = current_rgb[2] / transitiontime;
    }
  });

  server.on("/get", []() {
    server.send(200, "text/plain", "{\"R\":" + (String)rgb[0] + ", \"G\": " + (String)rgb[1] + ", \"B\":" + (String)rgb[2] + ", \"bri\":" + (String)bri + ", \"xy\": [" + (String)x + "," + (String)y + "], \"ct\":" + (String)ct + ", \"sat\": " + (String)sat + ", \"hue\": " + (String)hue + ", \"colormode\":" + color_mode + "}");
  });

  server.on("/detect", []() {
    server.send(200, "text/plain", "{\"hue\": \"bulb\",\"lights\": 1,\"type\": \"rgb\",\"mac\": \"" + String(mac[5], HEX) + ":"  + String(mac[4], HEX) + ":" + String(mac[3], HEX) + ":" + String(mac[2], HEX) + ":" + String(mac[1], HEX) + ":" + String(mac[0], HEX) + "\"}");
  });

  server.on("/reset", []() {
    server.send(200, "text/plain", "reset");
    ESP.reset();
  });


  server.onNotFound(handleNotFound);

  server.begin();
}

void loop() {
  ArduinoOTA.handle();
  server.handleClient();
  lightEngine();
}


void lightEngine() {
  if (light_state) {
    if (rgb[0] != current_rgb[0] || rgb[1] != current_rgb[1] || rgb[2] != current_rgb[2]) {
      if (rgb[0] != current_rgb[0]) current_rgb[0] += step_level[0];
      if (rgb[1] != current_rgb[1]) current_rgb[1] += step_level[1];
      if (rgb[2] != current_rgb[2]) current_rgb[2] += step_level[2];
      if ((step_level[0] > 0.0 && current_rgb[0] > rgb[0]) || (step_level[0] < 0.0 && current_rgb[0] < rgb[0])) current_rgb[0] = rgb[0];
      if ((step_level[1] > 0.0 && current_rgb[1] > rgb[1]) || (step_level[1] < 0.0 && current_rgb[1] < rgb[1])) current_rgb[1] = rgb[1];
      if ((step_level[2] > 0.0 && current_rgb[2] > rgb[2]) || (step_level[2] < 0.0 && current_rgb[2] < rgb[2])) current_rgb[2] = rgb[2];
      analogWrite(red_pin, current_rgb[0] * 4);
      analogWrite(green_pin, current_rgb[1] * 4);
      analogWrite(blue_pin, current_rgb[2] * 4);
    }
  } else {
    if (current_rgb[0] != 0 || current_rgb[1] != 0 || current_rgb[2] != 0) {
      if (current_rgb[0] != 0) current_rgb[0] -= step_level[0];
      if (current_rgb[1] != 0) current_rgb[1] -= step_level[1];
      if (current_rgb[2] != 0) current_rgb[2] -= step_level[2];
      if (current_rgb[0] < 0) current_rgb[0] = 0;
      if (current_rgb[1] < 0) current_rgb[1] = 0;
      if (current_rgb[2] < 0) current_rgb[2] = 0;
      analogWrite(red_pin, current_rgb[0] * 4);
      analogWrite(green_pin, current_rgb[1] * 4);
      analogWrite(blue_pin, current_rgb[2] * 4);
    }
  }
  delay(2);
}
