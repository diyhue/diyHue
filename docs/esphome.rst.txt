ESPHome
========

ESPHome currently only works with one light per ESPHome device. This protocol will even work with switches that are mapped as lights in ESPHome, making it very flexible and ideal for a large variety of devices.

Supported modes of operation are:

* RGBW
* CT
* RGB
* Dimmable
* Toggle

To add the device to diyHue, simply configure it using the information below and search for lights. The devices should be automatically imported into diyHue with the correct information.

General Configuration
---------------------

All devices must have a text sensor:

.. code-block:: YAML

  text_sensor:
    - platform: template
      name: "light_id"
      id: light_id
      lambda: |-
        char response[100];
        memset( response, 0, 100 );
        strcat( response, "esphome_diyhue_light;");
        strcat( response, id(wifi_info_mac_address).state.c_str());
        strcat( response, ";");
        strcat( response, App.get_name().c_str());
        strcat( response, ";CT_BOOST;RGB_BOOST" ); // ;CT_BOOST;RGB_BOOST values go here; Replace with 0 to disable
        return { response };
      update_interval: 24h

    - platform: wifi_info
      mac_address:
        name: MAC Address
        id: wifi_info_mac_address

Configurable options:

* ``CT_BOOST``: this value is utilized by diyHue to increase/decrease the default brightness of the CT light. Set this value to 0 to disable the feature. Must be an integer.
* ``RGB_BOOST``: same as CT_BOOST except will apply for the RGB component of the light.

**Important: CT_BOOST and RGB_BOOST must have a numeral value regardless of the bulb's capabilities. For bulbs that are dimmable and toggle, simply set these values to 0.**

The alert switch will be called when the bulb is requested to be located. As it stands now, it is not ideal as it does not return the light to the original state.

Entertainment Mode
------------------

The configuration for entertainment mode differs from the configuration here which does not include entertainment mode. The full code can be found in the ``Lights`` repository. The primary differences are:

.. code-block:: YAML

  NOTE the method is no longer supported by the current ESPHome version
  includes:
    - diyhueasyncudp.h
  libraries:
    - ESPAsyncUDP@697c75a025

  custom_component:
  - lambda: |-
      auto diyhue = new diyhueudp();
      return {diyhue};

These lines install the required library, the entertainment component, and initializes it. Additionally, be sure to copy the AsyncUDP component to the ESPHome directory. 


RGBW
---------

Including a white_led and a color_led light in the configuration will allow diyHue to automatically detect the devices as an RGBW device. 

CT
---------

Include a white_led light to mark the light as a CT light.

RGB
---------

Include a color_led light to mark the light as a RGB light.

Dimmable
---------

Include a dimmable_led light to mark the light as a Dimmable light.

Toggle
---------

Include a toggle_led light to mark the light as a Toggle light.

Sample Configuration
--------------------

This is a sample configuration for a RGBW light, namely the `Feit Electric Smart Bulb <https://templates.blakadder.com/feit_electric-OM60RGBWCAAG.html>`_. This configuration can be modified using the above information to integrate practically any type of light ESPHome supports with diyHue.

.. code-block:: YAML

  esphome:
    name: light1
    platform: ESP8266
    board: esp01_1m

  ota:
    password: "redacted"
      
  wifi:
    ssid: "redacted"
    password: "redacted"
    
    ap:
     ssid: "ESPhome light1"
    
  # Enable logging
  logger:
    level: DEBUG

  # Enable Home Assistant API
  api:
    password: "redacted"

  power_supply:
    - id: 'fast_led_pwr'
      pin: GPIO13

  output:
    - platform: esp8266_pwm
      pin: GPIO5
      id: cold_white_gpio
      frequency: 4000 Hz
      inverted: False
      min_power: 0
      max_power: 1
      
    - platform: esp8266_pwm
      pin: GPIO12
      id: warm_white_gpio
      frequency: 4000 Hz
      inverted: False
      min_power: 0
      max_power: 1
      
  light:
    - platform: cwww
      id: white_led
      name: "white_led"
      cold_white: cold_white_gpio
      warm_white: warm_white_gpio
      cold_white_color_temperature: 6500 K
      warm_white_color_temperature: 2000 K
      gamma_correct: 0.8
      default_transition_length: 0.4s

    - platform: fastled_spi
      id: color_led
      chipset: SM16716
      data_pin: GPIO14
      clock_pin: GPIO4
      power_supply: fast_led_pwr
      num_leds: 1
      rgb_order: BGR
      name: "color_led"
      default_transition_length: 0.4s
      gamma_correct: 0.8
      effects:
        - random:
            name: Random Effect With Custom Values
            transition_length: 5s
            update_interval: 3s

  text_sensor:
    - platform: template
      name: "light_id"
      id: light_id
      lambda: |-
        char response[100];
        memset( response, 0, 100 );
        strcat( response, "esphome_diyhue_light;");
        strcat( response, id(wifi_info_mac_address).state.c_str());
        strcat( response, ";");
        strcat( response, App.get_name().c_str());
        strcat( response, ";CT_BOOST;RGB_BOOST" ); // ;CT_BOOST;RGB_BOOST values go here; Replace with 0 to disable
        return { response };
      update_interval: 24h

    - platform: wifi_info
      mac_address:
        name: MAC Address
        id: wifi_info_mac_address
      
  switch:
    - platform: template
      name: alert
      id: alert
      optimistic: true
      turn_on_action:
        - light.turn_off: color_led
        - light.turn_on:
            id: white_led
            brightness: 100%
            color_temperature: 4000 K
        - delay: 1s
        - light.turn_on:
            id: white_led
            brightness: 10%
            color_temperature: 4000 K
        - delay: 1s
        - light.turn_on:
            id: white_led
            brightness: 100%
            color_temperature: 4000 K
        - delay: 1s
        - light.turn_on:
            id: white_led
            brightness: 10%
            color_temperature: 4000 K
        - delay: 1s
        - light.turn_on:
            id: white_led
            brightness: 100%
            color_temperature: 4000 K
        - switch.turn_off: alert
            
  web_server:
    port: 80