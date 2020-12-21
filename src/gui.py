import lvgl as lv

# lvgl must be initialized before any lvgl function is called or object/struct is constructed!
lv.init();

class ColorBgStyle(lv.style_t):
    def __init__(self, color):
        super().__init__()
        self.set_bg_opa(lv.STATE.DEFAULT, lv.OPA.COVER);
        self.set_bg_color(lv.STATE.DEFAULT, lv.color_hex3(color))

class Gui:
    def init_gui_esp32(self):

        import lvesp32

        # Initialize ILI9341 display
        from ili9XXX import ili9341

        self.disp = ili9341(miso=19, mosi=23, clk=18, cs=5, dc=32, rst=27, spihost=1, power=-1, backlight=33, backlight_on=1, mhz=80, factor=4, hybrid=True)

        # Register xpt2046 touch driver
        from xpt2046 import xpt2046

        self.touch = xpt2046(cs=26, spihost=1, mhz=5, max_cmds=16, cal_x0 = 3783, cal_y0 = 3948, cal_x1 = 242, cal_y1 = 423, transpose = True, samples = 3)

    def __init__(self, screen):
        
        # initialize esp32
        self.init_gui_esp32()

        # Create the main screen and load it.
        self.screen_main = screen()
        lv.scr_load(self.screen_main)
