#include <Arduino.h>

#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h>
#include <EEPROM.h>
#include "pwm.c"

#define PWM_CHANNELS 5
const uint32_t period = 1024;

//define pins
uint32 io_info[PWM_CHANNELS][3] = {
  // MUX, FUNC, PIN
  {PERIPHS_IO_MUX_MTCK_U,  FUNC_GPIO13, 13},
  {PERIPHS_IO_MUX_MTMS_U,  FUNC_GPIO14, 14},
  {PERIPHS_IO_MUX_MTDI_U,  FUNC_GPIO12, 12},
  {PERIPHS_IO_MUX_GPIO4_U, FUNC_GPIO4 ,  4},
  {PERIPHS_IO_MUX_GPIO5_U, FUNC_GPIO5 ,  5},
};

// initial duty: all off
uint32 pwm_duty_init[PWM_CHANNELS] = {0, 0, 0, 0, 0};


//#define USE_STATIC_IP //! uncomment to enable Static IP Adress
#ifdef USE_STATIC_IP
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);
#endif

uint8_t rgb_cct[5], color_mode, scene;
bool light_state, in_transition;
int transitiontime, ct, hue, bri, sat;
float step_level[5], current_rgb_cct[5], x, y;
byte mac[6];

ESP8266WebServer server(80);

void convert_hue()
{
  double      hh, p, q, t, ff, s, v;
  long        i;

  rgb_cct[3] = 0;
  s = sat / 255.0;
  v = bri / 255.0;

  if (s <= 0.0) {      // < is bogus, just shuts up warnings
    rgb_cct[0] = v;
    rgb_cct[1] = v;
    rgb_cct[2] = v;
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
      rgb_cct[0] = v * 255.0;
      rgb_cct[1] = t * 255.0;
      rgb_cct[2] = p * 255.0;
      break;
    case 1:
      rgb_cct[0] = q * 255.0;
      rgb_cct[1] = v * 255.0;
      rgb_cct[2] = p * 255.0;
      break;
    case 2:
      rgb_cct[0] = p * 255.0;
      rgb_cct[1] = v * 255.0;
      rgb_cct[2] = t * 255.0;
      break;

    case 3:
      rgb_cct[0] = p * 255.0;
      rgb_cct[1] = q * 255.0;
      rgb_cct[2] = v * 255.0;
      break;
    case 4:
      rgb_cct[0] = t * 255.0;
      rgb_cct[1] = p * 255.0;
      rgb_cct[2] = v * 255.0;
      break;
    case 5:
    default:
      rgb_cct[0] = v * 255.0;
      rgb_cct[1] = p * 255.0;
      rgb_cct[2] = q * 255.0;
      break;
  }

}

void convert_xy()
{
  float z = 1.0f - x - y;

  // sRGB D65 conversion
  float r =  x * 3.2406f - y * 1.5372f - z * 0.4986f;
  float g = -x * 0.9689f + y * 1.8758f + z * 0.0415f;
  float b =  x * 0.0557f - y * 0.2040f + z * 1.0570f;

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

  rgb_cct[0] = (int) (r * bri); rgb_cct[1] = (int) (g * bri); rgb_cct[2] = (int) (b * bri); rgb_cct[3] = 0; rgb_cct[4] = 0;
}

void convert_ct() {
  rgb_cct[0] = 0;
  rgb_cct[1] = 0;
  rgb_cct[2] = 0;

  uint8 percent_warm = ((ct - 150) * 100) / 350;

  rgb_cct[3] = (bri * percent_warm) / 100;
  rgb_cct[4] =  (bri * (100 - percent_warm)) / 100;

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

void lightEngine() {
  for (uint8_t color = 0; color < PWM_CHANNELS; color++) {
    if (light_state) {
      if (rgb_cct[color] != current_rgb_cct[color] ) {
        in_transition = true;
        current_rgb_cct[color] += step_level[color];
        if ((step_level[color] > 0.0f && current_rgb_cct[color] > rgb_cct[color]) || (step_level[color] < 0.0f && current_rgb_cct[color] < rgb_cct[color])) current_rgb_cct[color] = rgb_cct[color];
        pwm_set_duty((int)(current_rgb_cct[color] * 4), color);
        pwm_start();
      }
    } else {
      if (current_rgb_cct[color] != 0) {
        in_transition = true;
        current_rgb_cct[color] -= step_level[color];
        if (current_rgb_cct[color] < 0.0f) current_rgb_cct[color] = 0;
        pwm_set_duty((int)(current_rgb_cct[color] * 4), color);
        pwm_start();
      }
    }
  }
  if (in_transition) {
    delay(6);
    in_transition = false;
  }
}

void setup() {
  EEPROM.begin(512);

  for (uint8_t ch = 0; ch < PWM_CHANNELS; ch++) {
    pinMode(io_info[ch][2], OUTPUT);
  }

  pwm_init(period, pwm_duty_init, PWM_CHANNELS, io_info);
  pwm_start();

#ifdef USE_STATIC_IP
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
#endif

  apply_scene(EEPROM.read(2));
  step_level[0] = rgb_cct[0] / 150.0; step_level[1] = rgb_cct[1] / 150.0; step_level[2] = rgb_cct[2] / 150.0; step_level[3] = rgb_cct[3] / 150.0; step_level[4] = rgb_cct[4] / 150.0;

  if (EEPROM.read(1) == 1 || (EEPROM.read(1) == 0 && EEPROM.read(0) == 1)) {
    light_state = true;
    for (uint8_t i = 0; i < 200; i++) {
      lightEngine();
    }
  }
  WiFiManager wifiManager;
  wifiManager.autoConnect("New Hue Light");
  if (! light_state)  {
    // Show that we are connected
    pwm_set_duty(100, 1);
    pwm_start();
    delay(500);
    pwm_set_duty(0, 1);
    pwm_start();
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

  server.on("/switch", []() {
    server.send(200, "text/plain", "OK");
    int button;
    for (uint8_t i = 0; i < server.args(); i++) {
      if (server.argName(i) == "button") {
        button = server.arg(i).toInt();
      }
    }
    if (button == 1000) {
      if (light_state == false) {
        light_state = true;
        scene = 0;
      } else {
        apply_scene(scene);
        scene++;
        if (scene == 11) {
          scene = 0;
        }
      }
    } else if (button == 2000) {
      if (light_state == false) {
        bri = 30;
        light_state = true;
      } else {
        bri += 30;
      }
      if (bri > 255) bri = 255;
      if (color_mode == 1) convert_xy();
      else if (color_mode == 2) convert_ct();
      else if (color_mode == 3) convert_hue();
    } else if (button == 3000 && light_state == true) {
      bri -= 30;
      if (bri < 1) bri = 1;
      else {
        if (color_mode == 1) convert_xy();
        else if (color_mode == 2) convert_ct();
        else if (color_mode == 3) convert_hue();
      }
    } else if (button == 4000) {
      light_state = false;
    }
    for (uint8_t color = 0; color < PWM_CHANNELS; color++) {
      if (light_state) {
        step_level[color] = (rgb_cct[color] - current_rgb_cct[color]) / 54;
      } else {
        step_level[color] = current_rgb_cct[color] / 54;
      }
    }
  });


  server.on("/set", []() {
    light_state = true;
    float transitiontime = 4;
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
        rgb_cct[0] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "g") {
        rgb_cct[1] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "b") {
        rgb_cct[2] = server.arg(i).toInt();
        color_mode = 0;
      }
      else if (server.argName(i) == "w") {
        rgb_cct[3] = server.arg(i).toInt();
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
          current_rgb_cct[0] = 0; current_rgb_cct[1] = 0; current_rgb_cct[2] = 0; current_rgb_cct[3] = 0;
        } else {
          current_rgb_cct[0] = 255; current_rgb_cct[1] = 255; current_rgb_cct[2] = 255; current_rgb_cct[3] = 255;
        }
      }
      else if (server.argName(i) == "transitiontime") {
        transitiontime = server.arg(i).toInt();
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
    transitiontime *= 16;
    for (uint8_t color = 0; color < PWM_CHANNELS; color++) {
      if (light_state) {
        step_level[color] = (rgb_cct[color] - current_rgb_cct[color]) / transitiontime;
      } else {
        step_level[color] = current_rgb_cct[color] / transitiontime;
      }
    }
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
    server.send(200, "text/plain", "{\"hue\": \"bulb\",\"lights\": 1,\"modelid\": \"LCT015\",\"mac\": \"" + String(mac[5], HEX) + ":"  + String(mac[4], HEX) + ":" + String(mac[3], HEX) + ":" + String(mac[2], HEX) + ":" + String(mac[1], HEX) + ":" + String(mac[0], HEX) + "\"}");
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
        current_rgb_cct[0] = 0; current_rgb_cct[1] = 0; current_rgb_cct[2] = 0; current_rgb_cct[3] = 0;
      } else {
        current_rgb_cct[3] = 255;
      }
    }
    for (uint8_t color = 0; color < PWM_CHANNELS; color++) {
      if (light_state) {
        step_level[color] = ((float)rgb_cct[color] - current_rgb_cct[color]) / transitiontime;
      } else {
        step_level[color] = current_rgb_cct[color] / transitiontime;
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

void loop() {
  ArduinoOTA.handle();
  server.handleClient();
  lightEngine();
}
