#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

extern "C" {
#include "gpio.h"
#include "user_interface.h"
}

const char* ssid = "__SSID__";
const char* password = "__PASSWORD__";


//connect one Button to GPIO2 and one button to RX-Pin (GPIO3)
#define button1_pin 2
#define button2_pin 3

bool btn1_trig = false;
bool btn1_state = HIGH;
bool btn2_trig = false;
bool btn2_state = HIGH;


const char* switchType = "ZGPSwitch";

const char* bridgeIp = "192.168.178.45";

//Static adresses are no longer needed, because we use a Powersupply!
//DHCP FTW :)

//#define USE_STATIC_IP //! uncomment to enable Static IP Adress
#ifdef USE_STATIC_IP
IPAddress strip_ip ( 192,  168,   0,  95); // choose an unique IP Adress
IPAddress gateway_ip ( 192,  168,   0,   1); // Router IP
IPAddress subnet_mask(255, 255, 255,   0);
#endif

int counter;
byte mac[6];

void goingToSleep() {
  /*yield();
    delay(100);
    ESP.deepSleep(0);
    yield();*/
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

  Serial.println(String("GET ") + url + " HTTP/1.1\r\n" +
                 "Host: " + bridgeIp + "\r\n" +
                 "Connection: close\r\n\r\n");
}


void ISR_S1() {
  for (int i = 0; i < 5000; i++)
  {
    _NOP();
  }

  btn1_trig = true;
  if (digitalRead(button1_pin) == HIGH)
  {
    //Serial.println("S1_Rising!");
    btn1_state = HIGH;
  }
  else
  {
    //Serial.println("S1_Falling!");
    btn1_state = LOW;
  }
}



void ISR_S2() {

  for (int i = 0; i < 5000; i++)
  {
    _NOP();
  }

  btn2_trig = true;

  if (digitalRead(button2_pin) == HIGH)
  {
    //Serial.println("S2_Rising!");
    btn2_state = HIGH;
  }
  else
  {
    //Serial.println("S2_Falling!");
    btn2_state = LOW;
  }

}


void setup() {

  Serial.begin(250000);
  Serial.println();
  Serial.println("Setup!");

  pinMode(0, OUTPUT);
  digitalWrite(0, LOW);

  pinMode(16, OUTPUT);
  pinMode(button1_pin, INPUT);
  pinMode(button2_pin, INPUT);
  //pinMode(button3_pin, INPUT);
  //pinMode(button4_pin, INPUT);


  attachInterrupt(digitalPinToInterrupt(button1_pin), ISR_S1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(button2_pin), ISR_S2, CHANGE);



  digitalWrite(16, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
#ifdef USE_STATIC_IP
  WiFi.config(strip_ip, gateway_ip, subnet_mask);
#endif

  WiFi.macAddress(mac);

  while (WiFi.status() != WL_CONNECTED) {
    delay(50);
  }
  Serial.println("Connected");

  ArduinoOTA.begin();

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

  if (digitalRead(button1_pin) == LOW)
    btn1_state = LOW;

  if (digitalRead(button2_pin) == LOW)
    btn2_state = LOW;

}

void loop() {
  ArduinoOTA.handle();
  delay(1);

  //Serial.println("read...");
  delay(10);


  if (btn1_trig == true)
  {
    btn1_trig = false;
    if (btn1_state == HIGH)
      sendHttpRequest(34);
    else
      sendHttpRequest(16);
  }


  if (btn2_trig == true)
  {
    btn2_trig = false;
    if (btn2_state == HIGH)
      sendHttpRequest(17);
    else
      sendHttpRequest(18);
  }

  /*if (digitalRead(button1_pin) == HIGH && button1_high == false) {
    sendHttpRequest(34);
    button1_high = true;
    }

    if (digitalRead(button1_pin) == LOW && button1_high == true) {
    sendHttpRequest(16);
    button1_high = false;
    }

    if (digitalRead(button2_pin) == HIGH && button2_high == false) {
    sendHttpRequest(17);
    button2_high = true;
    }

    if (digitalRead(button2_pin) == LOW && button2_high == true) {
    sendHttpRequest(18);
    button2_high = false;
    }*/

  /*if (digitalRead(button2_pin) == HIGH) {
    sendHttpRequest(18);
    counter = 0;
    int i = 0;
    while (digitalRead(button2_pin) == HIGH && i < 20) {
      delay(20);
      i++;
    }
    }
    if (digitalRead(button3_pin) == HIGH) {
    sendHttpRequest(17);
    counter = 0;
    int i = 0;
    while (digitalRead(button3_pin) == HIGH && i < 20) {
      delay(20);
      i++;
    }
    }
    if (digitalRead(button4_pin) == HIGH) {
    sendHttpRequest(18);
    counter = 0;
    int i = 0;
    while (digitalRead(button4_pin) == HIGH && i < 20) {
      delay(20);
      i++;
    }
    }*/
  /*if (counter == 5000) {
    goingToSleep();
    } else {
    counter++;
    }*/

  delay(500);
}
