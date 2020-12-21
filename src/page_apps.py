#
# apps.py
#
# Application "launcher"
#

import sys, machine, uos
from uio import IOBase 
import _thread

import gui
import lvgl as lv
            
class Page_Apps:
    def exception_str(e):
        from uio import StringIO
        s=StringIO(); sys.print_exception(e, s)  
        s=s.getvalue().split('\n');
        l = len(s)
        line = s[l-3].split(',')[1].strip();
        error = s[l-2].strip();

        return "Error in "+line+"\n"+error;

    class Console(lv.label):
        class Wrapper(IOBase):
            def __init__(self):
                self.buffer = ""

            def write(self, data):
                self.buffer += data.decode('ascii').replace('\r', '')
            
            def get_buffer(self):
                retval = self.buffer
                self.buffer = ""        
                return retval
        
        def watcher(self, data):
            d = self.wrapper.get_buffer()
            if d != "": self.ins_text(lv.LABEL_POS.LAST, d);
        
            if not self.running:
                uos.dupterm(None)
                self.task.set_repeat_count(0);
                if self.done_cb:
                    self.done_cb()

        def execute(self, code):
            try:
                exec(code, {} )
            except Exception as e:
                print(Page_Apps.exception_str(e))
            
            self.running = False
        
        def __init__(self, *args, **kwds):
            super().__init__(*args, **kwds)
            self.set_text("")
            self.set_long_mode(lv.label.LONG.BREAK);

        def run(self, code, done_cb = None):
            self.done_cb = done_cb
        
            # start wrapper to catch script output
            self.wrapper = self.Wrapper()
            uos.dupterm(self.wrapper)

            # run script in background
            self.running = True
            _thread.start_new_thread( self.execute, ( code, ) )

            # start task to read text from wrapper and display it in label
            self.task = lv.task_create(self.watcher, 100, lv.TASK_PRIO.MID, None);

    def on_reload_btn(self, obj, event):
        if event == lv.EVENT.CLICKED:
            self.reload();
        
    def reload(self):
        self.list.clean()
        
        # scan controller flash for apps
        i = uos.ilistdir("apps")
        for f in i:
            if f[0].endswith(".py"):
                list_btn = self.list.add_btn(lv.SYMBOL.FILE, f[0]);
                list_btn.set_event_cb(self.on_app_btn);

    def __init__(self, page):
        self.page = page
        page.add_style(lv.obj.PART.MAIN, gui.ColorBgStyle(0xffd))

        # reload button
        self.reload_btn = lv.btn(page)
        self.reload_btn.align(page, lv.ALIGN.IN_TOP_MID, 0, 8)
        self.reload_btn.set_event_cb(self.on_reload_btn)
        label = lv.label(self.reload_btn)
        label.set_text(lv.SYMBOL.REFRESH);          

        # List of Apps
        self.list = lv.list(page)
        self.list.set_size(200, 190);
        self.list.align(page, lv.ALIGN.IN_TOP_MID, 0, 62)

        self.reload()

    def run_in_console(self, name, code):
        def done_cb():
            self.close_btn.set_click(True);
        
        console = self.Console(self.win)
        console.set_width(210);
        
        # we cannot stop threads, so disable the close
        # button while thread runs
        self.close_btn.set_click(False);
        console.run(code, done_cb)

    def on_app_btn(self, obj, event):
        def on_close(obj, evt):
            lv.win.close_event_cb(lv.win.__cast__(obj), evt)                
                    
        if event == lv.EVENT.CLICKED:
            name = lv.list.__cast__(obj).get_btn_text()[:-3]

            # load code
            try:
                f = open("apps/"+name+".py")
                code = f.read()
                f.close()
            except:
                # TODO: handle load error
                return

            # create window to run the app in
            self.win = lv.win(lv.scr_act())
            self.win.set_title(name)
            
            # add close button to the header
            self.close_btn = self.win.add_btn_right(lv.SYMBOL.CLOSE)
            self.close_btn.set_event_cb(on_close)

            self.run_in_console(name, code)
