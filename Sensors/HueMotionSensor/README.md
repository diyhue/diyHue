## How Is working

Hue Motion sensor need to send the folowing informations to bridge:
 - light level (default is at every 20 minutes)
 - when motion is detectet (instant)
 - when there is no motions enymore (30 seconds after last motion detected)
 
Because deepsleep mode is used to preserve battery life the rtc memory is used to store the last state.
In order to solve rf interferences issue of the previews version now esp8266 is wake up in non rf mode, read the GPIO pin states and then reset in default rf mode to send the data. This will add a very small delay (<500ms).

## Circuit diagram

![Circuit Diagram](https://raw.githubusercontent.com/mariusmotea/diyHue/develop/Images/Hue_Motion_sensor_circuit_prototype_v2.png)

## Prototypes

![Prototype1](https://raw.githubusercontent.com/mariusmotea/diyHue/develop/Images/Motion_Sensor_1.jpg)

![Prototype1](https://raw.githubusercontent.com/mariusmotea/diyHue/develop/Images/Motion_Sensor_2.jpg)

![Prototype1](https://raw.githubusercontent.com/mariusmotea/diyHue/develop/Images/Motion_Sensor_3.jpg)

![Prototype1](https://raw.githubusercontent.com/mariusmotea/diyHue/develop/Images/Motion_Sensor_4.jpg)
