## How Is working

When any button is pressed there will be a voltage difference on PNP transistor between the emitter and the base witch will trigger the NPN transistor and the ESP will receive a short pulse on RST pin for deep sleep wake up.
Because the circuit is supposed to be powered with Li-Ion battery there is a battery level monitor integrated witch will stop the operation when this become too low.
OTA firmware upgrade cam be activated by pressing button 1 and 4 in the same time (led will flash 5 times).
Is mandatory to set wifi name, wifi password, bridge emulator and static ip fields in the sketch header.

## Circuit diagram

![Circuit Diagram](https://github.com/mariusmotea/diyHue/raw/master/Images/Hue_Tap-Dimmer_switch_circuit_prototype.png)
