#
# main.py
#

import gui

import sys, time
import machine, os

import lvgl as lv

import page_wifi
import page_apps

class Screen_Main(lv.obj):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.tabview = lv.tabview(self)

        page_wifi.Page_WiFi(self.tabview.add_tab("WiFi"))
        page_apps.Page_Apps(self.tabview.add_tab("Apps"))

# run the user interface
g = gui.Gui(Screen_Main)
