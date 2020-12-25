import gui
import lvgl as lv
import network
import ujson

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
                cb(None)
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

        # use relative path on unix, absolute root else
        if hasattr(network, "UNIX"):
            self.config_file = "wifi.json"
        else:
            self.config_file = "/wifi.json"
        
        # read network config if possible
        config = self.read_wifi_config()
        
        # create dropdown, but disable it for now
        self.ssids = lv.dropdown(page)
        self.ssids.set_size(160, 32);
        self.ssids.align(page, lv.ALIGN.IN_TOP_MID, -20, 10)
        self.ssids.set_event_cb(self.on_ssid)

        # pre-populate list from stored wifi data if present
        if len(config["keys"]) > 0:
            ssids = list(config["keys"].keys())
            self.networks = [ { "ssid": x, "open": not config["keys"][x]} for x in ssids]
            self.set_ssid_list(ssids)
        else:
            self.ssids.set_options("")
            self.ssids.set_text("No Networks")
            self.ssids.set_show_selected(False)
            self.ssids.set_click(False);            
        
        # scan button
        self.scan_btn = lv.btn(page)
        self.scan_btn.set_size(32, 32);
        self.scan_btn.align(page, lv.ALIGN.IN_TOP_MID, 85, 10)
        self.scan_btn.set_event_cb(self.on_scan_btn)
        label = lv.label(self.scan_btn)
        label.set_text(lv.SYMBOL.REFRESH);          

        # info/status label
        self.label = lv.label(page)
        self.label.set_long_mode(lv.label.LONG.BREAK);
        self.label.set_width(210);
        self.label.set_text("");          
        self.label.set_align(lv.label.ALIGN.CENTER)
        self.label.align(page, lv.ALIGN.IN_TOP_MID, 0, 60)

        # enable wlan
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        
        # check if there is info about a last successfully
        # used network
        if "last" in config:
            print("Trying last network",config["last"],"...")
            self.connect(config["last"])

    def set_ssid_list(self, ssids):
        self.ssids.set_text("Select ...")        
        self.ssids.set_show_selected(False)
        self.ssids.set_click(True)
        self.ssids.set_options("\n".join(ssids))
            
    def on_ssid(self, obj, event):
        if event == lv.EVENT.VALUE_CHANGED:
            network = self.networks[obj.get_selected()]
            print("SEL:", self.networks[obj.get_selected()])
            if network["open"]:
                self.connect_with_key(network["ssid"], None)
            else:
                self.connect(network["ssid"])
        
    def on_scan_btn(self, obj, event):
        if event == lv.EVENT.CLICKED:
            self.networks = self.scan_wlan()
            self.set_ssid_list([x["ssid"] for x in self.networks])

    def connect_with_key(self, ssid, password):

        def connection_done(ok):
            self.ssids.set_click(True);
            self.scan_btn.set_click(True);
            
            if ok:
                self.write_key(ssid, password)

                self.ssids.set_show_selected(True)
                
                # find ssid in network list and select it
                for i in range(len(self.networks)):
                    if self.networks[i]["ssid"] == ssid:
                        self.ssids.set_selected(i)
                
                self.label.set_text("Connected\n\nSSID: "+ssid+"\nIP: "+self.wlan.ifconfig()[0]+"\nMDNS: ftduino.local");
                
                try:
                    import uwebserver
                    uwebserver.start()
                except Exception as e:
                    print("Webserver error:", e)

            else:
                self.label.set_text("Connection failed");
                
            self.task.set_repeat_count(0);
        
        def connect_task(task):
            self.cnt = self.cnt + 1

            if hasattr(self, "wlan"):
                if self.wlan.isconnected():
                    connection_done(True)
            else:
                # fake connection ok after 2.5 sec
                if self.cnt == 25:
                    connection_done(True)

            # timeout after 100 * 100ms = 10 seconds
            if self.cnt == 100:
                if hasattr(self, "wlan"):
                    self.wlan.active(False)  # interrupt the connection attempt
            
                connection_done(False)
                
        self.wlan.active(True)
        self.wlan.connect(ssid, password)

        # start a task that checks if connection was successful
        self.cnt = 0
        self.task = lv.task_create(connect_task, 100, lv.TASK_PRIO.MID, None);
        
    def scan_wlan(self):
        network_scanned = self.wlan.scan()
        networks = [ ]
        
        # sort by signal strength
        for n in sorted(network_scanned, key=lambda x: x[3], reverse=True):
            if not any(d['ssid'] == n[0].decode("ascii") for d in networks):
                networks.append( { "ssid": n[0].decode("ascii"), "open": n[4] == 0 })

        return networks  

    def read_wifi_config(self):
        try:
            with open(self.config_file) as fp:
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
            config["last"] = ssid
            try:
                with open(self.config_file, 'w') as fp:
                    ujson.dump(config, fp)
            except Exception as e:
                print("Error:", e)
    
    def connect(self, ssid):
        self.label.set_text("Connecting ...");

        # prevent user interaction while connecting
        self.ssids.set_click(False);      
        self.scan_btn.set_click(False);
                
        config = self.read_wifi_config()        
        if ssid in config["keys"]:
            self.connect_with_key(ssid, config["keys"][ssid])
            return
        
        def keyEntered(key):
            if key:
                self.connect_with_key(ssid, key)
            else:
                # user did not provide a key
                # make ui interactive, again
                self.ssids.set_click(True);      
                self.scan_btn.set_click(True);
                self.label.set_text("");
                
        self.kbd = KeyboardEntry("Enter key:", keyEntered, lv.scr_act())
    
