/*
  This can control bulbs with 3 pwm channels (red, gree and blue.
*/
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h>
#include <EEPROM.h>

#define light_name "Hue RGB Light" // Light name, change this if you se multiple lights for easy identification

#define PWM_CHANNELS 3

#define use_hardware_switch false // To control on/off state and brightness using GPIO/Pushbutton, set this value to true.
//For GPIO based on/off and brightness control, it is mandatory to connect the following GPIO pins to ground using 10k resistor
#define button1_pin 1 // on and brightness up
#define button2_pin 3 // off and brightness down

//define pins
uint8_t pins[PWM_CHANNELS] = {12, 13, 14}; //red, green, blue

//#define USE_STATIC_IP //! uncomment to enable Static IP Adress
#ifdef USE_STATIC_IP
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);
#endif

uint8_t colors[PWM_CHANNELS], bri, sat, color_mode, scene;
bool light_state, in_transition;
int ct, hue;
float step_level[PWM_CHANNELS], current_colors[PWM_CHANNELS], x, y;
byte mac[6];
byte packetBuffer[8];

ESP8266WebServer server(80);
WiFiUDP Udp;

void convert_hue()
{
  double      hh, p, q, t, ff, s, v;
  long        i;

  s = sat / 255.0;
  v = bri / 255.0;

  if (s <= 0.0) {      // < is bogus, just shuts up warnings
    colors[0] = v;
    colors[1] = v;
    colors[2] = v;
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
      colors[0] = v * 255.0;
      colors[1] = t * 255.0;
      colors[2] = p * 255.0;
      break;
    case 1:
      colors[0] = q * 255.0;
      colors[1] = v * 255.0;
      colors[2] = p * 255.0;
      break;
    case 2:
      colors[0] = p * 255.0;
      colors[1] = v * 255.0;
      colors[2] = t * 255.0;
      break;

    case 3:
      colors[0] = p * 255.0;
      colors[1] = q * 255.0;
      colors[2] = v * 255.0;
      break;
    case 4:
      colors[0] = t * 255.0;
      colors[1] = p * 255.0;
      colors[2] = v * 255.0;
      break;
    case 5:
    default:
      colors[0] = v * 255.0;
      colors[1] = p * 255.0;
      colors[2] = q * 255.0;
      break;
  }

}

void convert_xy()
{

  int optimal_bri = int( 10 + bri / 1.04);

  float Y = y;
  float X = x;
  float Z = 1.0f - x - y;

  // sRGB D65 conversion
  float r =  X * 3.2406f - Y * 1.5372f - Z * 0.4986f;
  float g = -X * 0.9689f + Y * 1.8758f + Z * 0.0415f;
  float b =  X * 0.0557f - Y * 0.2040f + Z * 1.0570f;

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

  colors[0] = (int) (r * optimal_bri); colors[1] = (int) (g * optimal_bri); colors[2] = (int) (b * optimal_bri);
}

void convert_ct() {
  int optimal_bri = int( 10 + bri / 1.04);
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
  
  colors[0] = r * (optimal_bri / 255.0f); colors[1] = g * (optimal_bri / 255.0f); colors[2] = b * (optimal_bri / 255.0f);
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

void apply_scene(uint8_t new_scene) {
  if ( new_scene == 0) {
    bri = 144; ct = 447; color_mode = 2; convert_ct();
  } else if ( new_scene == 1) {
    bri = 254; ct = 346; color_mode = 2; convert_ct();
  } else if ( new_scene == 2) {
    bri = 254; ct = 233; color_mode = 2; convert_ct();
  }  else if ( new_scene == 3) {
    bri = 254; ct = 156; color_mode = 2; convert_ct();
  }  else if ( new_scene == 4) {
    bri = 77; ct = 367; color_mode = 2; convert_ct();
  }  else if ( new_scene == 5) {
    bri = 254; ct = 447; color_mode = 2; convert_ct();
  }  else if ( new_scene == 6) {
    bri = 1; x = 0.561; y = 0.4042; color_mode = 1; convert_xy();
  }  else if ( new_scene == 7) {
    bri = 203; x = 0.380328; y = 0.39986; color_mode = 1; convert_xy();
  }  else if ( new_scene == 8) {
    bri = 112; x = 0.359168; y = 0.28807; color_mode = 1; convert_xy();
  }  else if ( new_scene == 9) {
    bri = 142; x = 0.267102; y = 0.23755; color_mode = 1; convert_xy();
  }  else if ( new_scene == 10) {
    bri = 216; x = 0.393209; y = 0.29961; color_mode = 1; convert_xy();
  }
}

void process_lightdata(float transitiontime) {
  if (color_mode == 1 && light_state == true) {
    convert_xy();
  } else if (color_mode == 2 && light_state == true) {
    convert_ct();
  } else if (color_mode == 3 && light_state == true) {
    convert_hue();
  }
  transitiontime *= 16;
  for (uint8_t color = 0; color < PWM_CHANNELS; color++) {
    if (light_state) {
      step_level[color] = (colors[color] - current_colors[color]) / transitiontime;
    } else {
      step_level[color] = current_colors[color] / transitiontime;
    }
  }
}

void lightEngine() {
  for (uint8_t color = 0; color < PWM_CHANNELS; color++) {
    if (light_state) {
      if (colors[color] != current_colors[color] ) {
        in_transition = true;
        current_colors[color] += step_level[color];
        if ((step_level[color] > 0.0f && current_colors[color] > colors[color]) || (step_level[color] < 0.0f && current_colors[color] < colors[color])) current_colors[color] = colors[color];
        analogWrite(pins[color], (int)(current_colors[color]));
      }
    } else {
      if (current_colors[color] != 0) {
        in_transition = true;
        current_colors[color] -= step_level[color];
        if (current_colors[color] < 0.0f) current_colors[color] = 0;
        analogWrite(pins[color], (int)(current_colors[color]));
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
      if (i < 30) {
        // there was a short press
        light_state = true;
      }
      else {
        // there was a long press
        bri += 56;
        if (bri > 254) {
          // don't increase the brightness more then maximum value
          bri = 254;
        }
      }
      process_lightdata(4);
    } else if (digitalRead(button2_pin) == HIGH) {
      int i = 0;
      while (digitalRead(button2_pin) == HIGH && i < 30) {
        delay(20);
        i++;
      }
      if (i < 30) {
        // there was a short press
        light_state = false;
      }
      else {
        // there was a long press
        bri -= 56;
        if (bri < 1) {
          // don't decrease the brightness less than minimum value.
          bri = 1;
        }
      }
      process_lightdata(4);
    }
  }
}

void setup() {
  EEPROM.begin(512);
  analogWriteFreq(1000);
  analogWriteRange(255);

  for (uint8_t pin = 0; pin < PWM_CHANNELS; pin++) {
    pinMode(pins[pin], OUTPUT);
    analogWrite(pins[pin], 0);
  }

#ifdef USE_STATIC_IP
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
#endif

  apply_scene(EEPROM.read(2));
  step_level[0] = colors[0] / 150.0; step_level[1] = colors[1] / 150.0; step_level[2] = colors[2] / 150.0; step_level[3] = colors[3] / 150.0;

  if (EEPROM.read(1) == 1 || (EEPROM.read(1) == 0 && EEPROM.read(0) == 1)) {
    light_state = true;
    for (uint8_t i = 0; i < 200; i++) {
      lightEngine();
    }
  }
  WiFiManager wifiManager;
  wifiManager.setConfigPortalTimeout(120);
  wifiManager.autoConnect(light_name);

  if (! light_state)  {
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
  Udp.begin(2100);

  pinMode(LED_BUILTIN, OUTPUT);     // Initialize the LED_BUILTIN pin as an output
  digitalWrite(LED_BUILTIN, HIGH);  // Turn the LED off by making the voltage HIGH
  if (use_hardware_switch == true) {
    pinMode(button1_pin, INPUT);
    pinMode(button2_pin, INPUT);
  }


  server.on("/set", []() {
    light_state = true;
    float transitiontime = 4.0;
    for (uint8_t i = 0; i < server.args(); i++) {
      if (server.argName(i) == "on") {
        if (server.arg(i) == "True" || server.arg(i) == "true") {
          if (EEPROM.read(1) == 0 && EEPROM.read(0) != 1) {
            EEPROM.write(0, 1);
            EEPROM.commit();
          }
          light_state = true;
        }
        else {
          if (EEPROM.read(1) == 0 && EEPROM.read(0) != 0) {
            EEPROM.write(0, 0);
            EEPROM.commit();
          }
          light_state = false;
        }
      }
      else if (server.argName(i) == "r") {
        colors[0] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "g") {
        colors[1] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "b") {
        colors[2] = server.arg(i).toInt();
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
        if (server.arg(i).toInt() != 0)
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
      else if (server.argName(i) == "alert" && server.arg(i) == "select") {
        if (light_state) {
          current_colors[0] = 0; current_colors[1] = 0; current_colors[2] = 0;
        } else {
          current_colors[0] = 255; current_colors[1] = 255; current_colors[2] = 255;
        }
      }
      else if (server.argName(i) == "transitiontime") {
        transitiontime = server.arg(i).toInt();
      }
    }
    server.send(200, "text/plain", "OK, x: " + (String)x + ", y:" + (String)y + ", bri:" + (String)bri + ", ct:" + ct + ", colormode:" + color_mode + ", state:" + light_state);
    process_lightdata(transitiontime);
  });

  server.on("/get", []() {
    String colormode;
    String power_status;
    power_status = light_state ? "true" : "false";
    if (color_mode == 1)
      colormode = "xy";
    else if (color_mode == 2)
      colormode = "ct";
    else if (color_mode == 3)
      colormode = "hs";
    server.send(200, "text/plain", "{\"on\": " + power_status + ", \"bri\": " + (String)bri + ", \"xy\": [" + (String)x + ", " + (String)y + "], \"ct\":" + (String)ct + ", \"sat\": " + (String)sat + ", \"hue\": " + (String)hue + ", \"colormode\": \"" + colormode + "\"}");
  });

  server.on("/detect", []() {
    char macString[50] = {0};
    sprintf(macString, "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    server.send(200, "text/plain", "{\"hue\": \"bulb\",\"lights\": 1,\"modelid\": \"LCT015\",\"name\": \"" light_name "\",\"mac\": \"" + String(macString) + "\"}");
  });

  server.on("/", []() {
    float transitiontime = 100;
    if (server.hasArg("startup")) {
      if (  EEPROM.read(1) != server.arg("startup").toInt()) {
        EEPROM.write(1, server.arg("startup").toInt());
        EEPROM.commit();
      }
    }

    if (server.hasArg("scene")) {
      if (server.arg("bri") == "" && server.arg("hue") == "" && server.arg("ct") == "" && server.arg("sat") == "") {
        if (  EEPROM.read(2) != server.arg("scene").toInt() && EEPROM.read(1) < 2) {
          EEPROM.write(2, server.arg("scene").toInt());
          EEPROM.commit();
        }
        apply_scene(server.arg("scene").toInt());
      } else {
        if (server.arg("bri") != "") {
          bri = server.arg("bri").toInt();
        }
        if (server.arg("hue") != "") {
          hue = server.arg("hue").toInt();
        }
        if (server.arg("sat") != "") {
          sat = server.arg("sat").toInt();
        }
        if (server.arg("ct") != "") {
          ct = server.arg("ct").toInt();
        }
        if (server.arg("colormode") == "1" && light_state == true) {
          convert_xy();
        } else if (server.arg("colormode") == "2" && light_state == true) {
          convert_ct();
        } else if (server.arg("colormode") == "3" && light_state == true) {
          convert_hue();
        }
        color_mode = server.arg("colormode").toInt();
      }
    } else if (server.hasArg("on")) {
      if (server.arg("on") == "true") {
        light_state = true; {
          if (EEPROM.read(1) == 0 && EEPROM.read(0) != 1) {
            EEPROM.write(0, 1);
          }
        }
      } else {
        light_state = false;
        if (EEPROM.read(1) == 0 && EEPROM.read(0) != 0) {
          EEPROM.write(0, 0);
        }
      }
      EEPROM.commit();
    } else if (server.hasArg("alert")) {
      if (light_state) {
        current_colors[0] = 0; current_colors[1] = 0; current_colors[2] = 0;
      } else {
        current_colors[0] = 254; current_colors[1] = 254; current_colors[2] = 254;
      }
    }
    for (uint8_t color = 0; color < PWM_CHANNELS; color++) {
      if (light_state) {
        step_level[color] = ((float)colors[color] - current_colors[color]) / transitiontime;
      } else {
        step_level[color] = current_colors[color] / transitiontime;
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
    http_content += "<title>"; http_content += light_name; http_content += " - Light Setup</title>";
    http_content += "<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">";
    http_content += "</head>";
    http_content += "<body>";
    http_content += "<fieldset>";
    http_content += "<h3>"; http_content += light_name; http_content += " - Light Setup</h3>";
    http_content += "<form class=\"pure-form pure-form-aligned\" action=\"/\" method=\"post\">";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"power\"><strong>Power</strong></label>";
    http_content += "<a class=\"pure-button"; if (light_state) http_content += "  pure-button-primary"; http_content += "\" href=\"/?on=true\">ON</a>";
    http_content += "<a class=\"pure-button"; if (!light_state) http_content += "  pure-button-primary"; http_content += "\" href=\"/?on=false\">OFF</a>";
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
    http_content += "<option "; if (EEPROM.read(2) == 1) http_content += "selected=\"selected\""; http_content += " value=\"1\">Read</option>";
    http_content += "<option "; if (EEPROM.read(2) == 2) http_content += "selected=\"selected\""; http_content += " value=\"2\">Concentrate</option>";
    http_content += "<option "; if (EEPROM.read(2) == 3) http_content += "selected=\"selected\""; http_content += " value=\"3\">Energize</option>";
    http_content += "<option "; if (EEPROM.read(2) == 4) http_content += "selected=\"selected\""; http_content += " value=\"4\">Bright</option>";
    http_content += "<option "; if (EEPROM.read(2) == 5) http_content += "selected=\"selected\""; http_content += " value=\"5\">Dimmed</option>";
    http_content += "<option "; if (EEPROM.read(2) == 6) http_content += "selected=\"selected\""; http_content += " value=\"6\">Nightlight</option>";
    http_content += "<option "; if (EEPROM.read(2) == 7) http_content += "selected=\"selected\""; http_content += " value=\"7\">Savanna sunset</option>";
    http_content += "<option "; if (EEPROM.read(2) == 8) http_content += "selected=\"selected\""; http_content += " value=\"8\">Tropical twilight</option>";
    http_content += "<option "; if (EEPROM.read(2) == 9) http_content += "selected=\"selected\""; http_content += " value=\"9\">Arctic aurora</option>";
    http_content += "<option "; if (EEPROM.read(2) == 10) http_content += "selected=\"selected\""; http_content += " value=\"10\">Spring blossom</option>";
    http_content += "</select>";
    http_content += "</div>";
    http_content += "<br>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"state\"><strong>State</strong></label>";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"bri\">Bri</label>";
    http_content += "<input id=\"bri\" name=\"bri\" type=\"text\" placeholder=\"" + (String)bri + "\">";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"hue\">Hue</label>";
    http_content += "<input id=\"hue\" name=\"hue\" type=\"text\" placeholder=\"" + (String)hue + "\">";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"sat\">Sat</label>";
    http_content += "<input id=\"sat\" name=\"sat\" type=\"text\" placeholder=\"" + (String)sat + "\">";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"ct\">CT</label>";
    http_content += "<input id=\"ct\" name=\"ct\" type=\"text\" placeholder=\"" + (String)ct + "\">";
    http_content += "</div>";
    http_content += "<div class=\"pure-control-group\">";
    http_content += "<label for=\"colormode\">Color</label>";
    http_content += "<select id=\"colormode\" name=\"colormode\">";
    http_content += "<option "; if (color_mode == 1) http_content += "selected=\"selected\""; http_content += " value=\"1\">xy</option>";
    http_content += "<option "; if (color_mode == 2) http_content += "selected=\"selected\""; http_content += " value=\"2\">ct</option>";
    http_content += "<option "; if (color_mode == 3) http_content += "selected=\"selected\""; http_content += " value=\"3\">hue</option>";
    http_content += "</select>";
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

void entertainment() {
  int packetSize = Udp.parsePacket();
  if (packetSize) {
    Udp.read(packetBuffer, packetSize);
    for (uint8_t color = 0; color < 3; color++) {
      analogWrite(pins[color - 1], (int)(packetBuffer[color]));
    }
  }
}

void loop() {
  ArduinoOTA.handle();
  server.handleClient();
  lightEngine();
  entertainment();
}
