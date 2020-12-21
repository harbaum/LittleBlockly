# LittleBlockly - LVGL, Micropython and Blockly

This project combines LVGL and Micropython with Blockly. A quick and
dirty video can be found [here](https://youtu.be/ahSjJkrcRJM).

The demo runs on an ESP32 WROVER connected to a ILI9341 based
2.2 inch 240x320 TFT touchscreen.

The required wiring (VCC/GND is shared by the touch):

| ESP32 | TFT | TOUCH |
|-------|---|---|
| 3V3 | VCC | |
| GND | GND | |
| 5 | CS | |
| 27 | RESET | |
| 32 | DC | |
| 23 | SDI(MOSI) | T_DIN |
| 18 | SCK | T_CLK|
| 33 | LED | |
| 23 | SDO(MOSI) | T_DO |
| 26 | | T_CS |

The ESP32 needs to be flashed with the [LVGL micropython
port](https://github.com/lvgl/lv_micropython).

All files from the src directory have to be copied to the ESP32's
flash storage.
