import gui
import lvgl as lv

# this should go into the GUI class
class KeyboardEntry(lv.obj):
    def __init__(self, title, cb, *args, **kwds):
        def kbd_event_cb(obj, evt):
            obj.def_event_cb(evt);
            
            if evt == lv.EVENT.DELETE:
                obj.get_parent().del_async();
                self.kbd = None              
            elif evt == lv.EVENT.CANCEL:
                obj.del_async();
            elif evt == lv.EVENT.APPLY:
                text = self.text.get_text()
                obj.del_async();
                cb(text)

        super().__init__(*args, **kwds)

        # styly of the background overlay
        self.style = lv.style_t()
        self.style.init();
        self.style.set_bg_opa(lv.STATE.DEFAULT, lv.OPA._100);
        self.style.set_bg_color(lv.STATE.DEFAULT, lv.color_hex3(0xeee));
    
        # create a base object for the modal background
        self.reset_style_list(lv.obj.PART.MAIN);
        self.add_style(lv.obj.PART.MAIN, self.style);
        self.set_pos(0, 0);
        self.set_size(240, 320);

        label = lv.label(self)
        label.set_text(title)
        label.align(self, lv.ALIGN.IN_TOP_MID, 0, 60)
        
        self.text = lv.textarea(self)
        self.text.set_text("");
        self.text.set_height(40);
        self.text.set_width(200);
        self.text.align(self, lv.ALIGN.IN_TOP_MID, 0, 100)

        self.kbd = lv.keyboard(self)
        self.kbd.set_event_cb(kbd_event_cb);
        self.kbd.set_cursor_manage(False);
        self.kbd.set_textarea(self.text);
        
        self.g = lv.group_t();
        self.g.add_obj(self.kbd);  
        lv.group_focus_obj(self.kbd);
        self.g.focus_freeze(True);
        
class Page_WiFi:
    def __init__(self, page):
        self.page = page

        page.add_style(lv.obj.PART.MAIN, gui.ColorBgStyle(0xfdd))

        # "Scan ..." button on top
        self.btn = lv.btn(page)
        self.btn.align(page, lv.ALIGN.IN_TOP_MID, 0, 8)
        self.btn.set_event_cb(self.on_btn)
        label = lv.label(self.btn)
        label.set_text("Scan ...");

        # List of WLANs below
        self.list = lv.list(page)
        self.list.set_size(200, 190);
        self.list.align(page, lv.ALIGN.IN_TOP_MID, 0, 63)

    def do_connect(self, ssid, password):

        def connection_done(ok):
            if ok:
                self.write_key(ssid, password)
                print(self.wlan.ifconfig())

                try:
                    import uwebserver
                    uwebserver.start()
                except Exception as e:
                    print("Error:", e)                    

            self.task.set_repeat_count(0);
            self.spinner.del_async();
        
        def connect_task(task):
            self.cnt = self.cnt + 1

            if hasattr(self, "wlan"):
                if self.wlan.isconnected():
                    connection_done(True)
            else:
                # fake connection ok after 2.5 sec
                if self.cnt == 25:
                    connection_done(True)

            # timeout after 50 * 100ms = 5 seconds
            if self.cnt == 50:
                if hasattr(self, "wlan"):
                    self.wlan.active(False)  # interrupt the connection attempt
            
                connection_done(False)
                
        # create spinner
        self.spinner = lv.spinner(lv.scr_act());
        self.spinner.set_size(100, 100);
        self.spinner.align(lv.scr_act(), lv.ALIGN.CENTER, 0, 0);

        if hasattr(self, "wlan"):
            self.wlan.active(True)
            if self.wlan.isconnected():
                self.spinner.del_async();

            self.wlan.connect(ssid, password)

        # start a task that checks if connection was successful
        self.cnt = 0
        self.task = lv.task_create(connect_task, 100, lv.TASK_PRIO.MID, None);
        
    def scan_wlan(self):
        import network
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        network_scanned = self.wlan.scan()
        networks = [ ]
        
        # sort by signal strength
        for n in sorted(network_scanned, key=lambda x: x[3], reverse=True):
            if not any(d['ssid'] == n[0].decode("ascii") for d in networks):
                networks.append( { "ssid": n[0].decode("ascii"), "open": n[4] == 0 })

        return networks  

    def read_wifi_config(self):
        try:
            import ujson
            with open('/wifi.json') as fp:
	        config = ujson.loads(fp.read())
            return config
        except Exception as e:
            config = { }

        if not "keys" in config:
            config["keys"] = {}
        return config

    def write_key(self, ssid, key):
        config = self.read_wifi_config()
        if not ssid in config["keys"]:
            config["keys"][ssid] = key
            try:
                import ujson
                with open('/wifi.json', 'w') as fp:
                    ujson.dump(config, fp)
            except Exception as e:
                print("Error:", e)
    
    def getKey(self, ssid):
        config = self.read_wifi_config()        
        if ssid in config["keys"]:
            self.do_connect(ssid, config["keys"][ssid])
            return
        
        def keyEntered(key):
            self.do_connect(ssid, key)
        
        self.kbd = KeyboardEntry("Enter key:", keyEntered, lv.scr_act())
    
    def on_btn(self, obj, event):
        def on_network_btn(obj, event):
            if event == lv.EVENT.CLICKED:
                ssid = lv.list.__cast__(obj).get_btn_text()
                network = list(filter(lambda x: x['ssid'] == ssid, self.networks))[0]

                if network["open"]:
                    self.do_connect(ssid, None)
                else:                
                    self.getKey(ssid)
        
        if event == lv.EVENT.CLICKED:
            self.list.clean();
            self.networks = self.scan_wlan()
            for n in self.networks:
                list_btn = self.list.add_btn(lv.SYMBOL.WIFI, n["ssid"]);
                list_btn.set_event_cb(on_network_btn);
