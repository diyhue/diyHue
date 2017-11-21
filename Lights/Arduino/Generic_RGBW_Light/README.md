# Custom light instruction

![Circuit Diagram](https://github.com/mariusmotea/diyHue/blob/master/Lights/Arduino/Generic_RGBW_Light/images/schematic.JPG)

Start with placing components on your board to make sure you got room for the paths/wires without soldering yourself into trouble :)

1. Solder Wemos headers

2. Solder the resistors in correct place. Make sure to leave room for the GPIO wire that will come later

3. Solder the path for gnd/negative across the board

4. Solder path for resistor <-> ground

5. Solder/wire the G pin on Wemos to the ground strip running across the board for common ground

6. Solder wires from GPIO pins to correct places: D1 = white, D7 = green, D6 = red, D5 = blue
   The wires go between the resistor and the 3 pin header for the mosfets and everything    connects to the left leg of the mosfet

7. Solder the 3 pin female headers

8. Solder wires with correct colors to the middle pin of the header

9. Insert Wemos and mosfets

You can use any 12v RGBW or RGBWW strip that has 5 connectors for this build. I recomend the RGBWW strips from what i have experienced so far, the RGBW ones dont make proper yellow/warm light.


![Top](https://github.com/mariusmotea/diyHue/blob/master/Lights/Arduino/Generic_RGBW_Light/images/Over.jpg)
![Back](https://github.com/mariusmotea/diyHue/blob/master/Lights/Arduino/Generic_RGBW_Light/images/Under.jpg)

## Components

[IRLB8721-TO220 MOSFETS (4x)](https://www.aliexpress.com/item/10PCS-IRLB8721-TO220-IRLB8721PBF-TO-220-free-shipping/32714364118.html)

[Wemos D1 mini (1x)](https://www.aliexpress.com/item/ESP8266-ESP12-ESP-12-WeMos-D1-Mini-WIFI-Dev-Kit-Development-Board-NodeMCU-Lua/32653918483.html)

[1k OHM resistor (4x)](https://www.aliexpress.com/item/100pcs-1-4W-Metal-Film-Resistor-1K-ohm-1KR-1-Tolerance-Precision-RoHS-Lead-Free-In/1851964338.html)

[Female Headers (4x)](https://www.aliexpress.com/item/10-10-pcs-Single-Row-Pin-Female-Header-Socket-2-54mm-Pitch-1-10p-12p-20p/32783590196.html)

[Prototyping board (1x)](https://www.aliexpress.com/item/20pcs-5x7-4x6-3x7-2x8-cm-double-Side-Copper-prototype-pcb-Universal-Board-for-Arduino/1847727667.html)


# Feican RGBW bulb

https://raw.githubusercontent.com/mariusmotea/diyHue/master/Images/Color_Dream_bulb_with_flash_replaced.jpg
