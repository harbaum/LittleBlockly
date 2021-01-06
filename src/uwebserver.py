import socket
import network
import espidf
import uos, ujson

import lvgl as lv

click = None

def check4file(fname):
    try:
        f = open(fname, "r")
        f.close()
        return True
    except:
        return False

def do_POST(hdr, s):
    global click
    
    # check if this was a "click" post
    url = hdr[0].split(' ')[1];
    if url.startswith("/click"):
        c = { }
        print("Click");
        parmstr = url.split("?")[1]
        for p in parmstr.split("&"):
            id,val = p.split("=")
            if id == "x": c["x"] = int(val);
            if id == "y": c["y"] = int(val);

        if "x" in c and "y" in c:
            print("Click:", c);
            c["reported"] = False;
            click = c
        
        return
    
    # iterate over all header lines to extract boundary and
    # content-length
    boundary = None
    clength = None
    for l in hdr:
        parts = l.split(':', 1)
        if len(parts) == 2:
            tag = parts[0].strip()
            if tag == "Content-Length":
                clength = int(parts[1])

            if tag == "Content-Type":
                ctype = parts[1].split(';')
                if len(ctype) == 2:
                    for ct in ctype:                            
                        ctp = ct.split('=')
                        if len(ctp) == 2:
                            if ctp[0].lower().strip() == "boundary":
                                boundary = "--" + ctp[1].strip()

    print("Boundary", boundary);
    print("Length", clength);

    if not boundary:
        print("No boundary");
        return

    # states:
    # 0 - wait for start boundary
    # 1 - wait for empty line ending header
    # 2 - data phase, wait for end boundary
    # 3 - done
    bcount = 0
    state = 0
    fp = None
    while state < 3 and (clength == None or bcount < clength):
        try:
            line = s.readline()
            bcount += len(line)
        except Exception as e:
            print("Exception in readline:", e);
            break

        if state == 1 and line == b'\r\n':
            state = state + 1
        else:
            try:
                # the last line ends with "\r\n" which is added by the
                # POST transfer. Remove that. This will actually remove
                # \r\n from any line which doesn't happen since cm and
                # blockly use single \n
                if len(line) > 1 and line[-2:] == b'\r\n':
                    line = line[:-2]
                
                line = line.decode('utf-8')
            except:
                # we cannot decode this. May be binary data. We don't care ...
                print("Trouble with line",str(line))
                return

            # use stripped line for header parsing
            sline = line.strip()

            if sline.startswith(boundary):
                if state == 0:
                    state = 1
                if state == 2:
                    if fp:
                        fp.close()
                        fp = None
                        
                    state = 1
            elif state == 1:
                # in state one parse the header lines for e.g. the file name
                cparts = sline.split(":", 1)
                if len(cparts) == 2 and cparts[0].strip() == "Content-Disposition":
                    dparts = cparts[1].split(';')
                    for dpart in dparts:
                        dp = dpart.split("=", 1)
                        if len(dp) == 2 and dp[0].strip() == "filename":
                            filename = "/apps/" + (dp[1].strip("\" "))
                            print("writing to", filename)
                            fp = open(filename, "wb")
                                        
            elif state == 2:
                if fp: fp.write(line)
                
def get_mimetype(ext):
    CONTENT_TYPES = {
        "html": "text/html",
        "css": "text/css",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "json": "application/json",
        "svg": "image/svg+xml",
        "png": "image/png",
        "svg": "image/svg+xml",
        "xml": "application/xml",
        "py": "text/x-python",
        "js": "application/javascript"
    }
    
    if ext in CONTENT_TYPES:
        return CONTENT_TYPES[ext]

    return "application/octet-stream"

def send_header(socket, code, mimetype = "text/html", compressed = False):
    socket.send('HTTP/1.1 '+code+'\n')
    socket.send('Content-Type: '+mimetype+'\n')
    if compressed:
        socket.send('Content-Encoding: gzip\n')
    socket.send('Connection: close\n\n')

def send_404(socket):
    send_header(socket, "404 Not found")
    socket.send("<html><h1>404</h1>Not found</html>")
    socket.close()

def send_file(socket, fname):
    try:
        f = open(fname, "rb")
        while True:
            data = f.read(32*1024)
            if not data: break

            print("Sending", len(data), "bytes");
            socket.send(data)
                
    except Exception as e:
        print("Sending file failed", e);
        
    socket.close()

def unquote(string):
    parts = string.split('%')
    result = parts[0]
    if len(parts) > 1:
        for part in parts[1:]:
            try:
                result += chr(int(part[:2], 16)) + part[2:]
            except:
                result += "%"+part

    return result

def accept_http_connect(http_server):
    def my_flush(drv, area, buf):
        data = buf.__dereference__(area.get_size() * lv.color_t.SIZE)
        try:
            client_socket.send(data);
        except Exception as e:
            print("Error:", e);
            
        # espidf.ili9xxx_flush(drv, area, buf)
        drv.flush_ready()
        
    client_socket, remote_addr = http_server.accept()
    print("Http connection from:", remote_addr)
    client_socket.settimeout(2)

    data = []

    print("Request:");
    # read via file descriptor
    while True:
        try:
            line = client_socket.readline()
        except Exception as e:
            print("read failed:", e);
            client_socket.close()
            return
            
        if not line or line == b'\r\n':
            break

        l = line.decode('utf-8').strip()
        print("  ", l);
        data.append(l)
            
    if len(data) == 0:
        print("empty request??")
        client_socket.close()
        return
    
    items = data[0].split(' ');
    if items[0] == "POST":
        do_POST(data, client_socket)

        # send reply
        send_header(client_socket, "200 OK")
        client_socket.send("<html>Ok</html>")            
        client_socket.close()
        return
            
    if items[0] == "GET":
        if items[1].startswith("/screen"):
            send_header(client_socket, "200 OK", "application/octet-stream")

            lv.scr_act().get_disp().driver.flush_cb = my_flush;
            lv.scr_act().invalidate()
            lv.refr_now(lv.disp_get_default())        
            lv.scr_act().get_disp().driver.flush_cb = espidf.ili9xxx_flush
            

            client_socket.close()
            return
            
        else:
            # ignore anything after ? if present                        
            fname = "/html"+items[1].split('?')[0]
            if fname[-1] == '/':
                fname = fname + "index.html"

            # check if file exists. May be compressed ...
            file_ok = False
            compressed = False
            if check4file(fname):
                file_ok = True
            if check4file(fname+".gz"):
                file_ok = True
                compressed = True

            # send file if ok, 404 otherwise
            if file_ok:
                mimetype = get_mimetype(fname.split('.')[-1])
                send_header(client_socket, "200 OK", mimetype, compressed)
            else:
                send_404(client_socket)
                return

            # use gzipped file
            if compressed: fname = fname + ".gz"

            send_file(client_socket, fname)
            
    print("tx done", remote_addr);

def input_callback(drv, data):
    global click

    if not click:
        data.state = lv.INDEV_STATE.REL
    elif click["reported"]:
        data.state = lv.INDEV_STATE.REL
        data.point.x = click["x"]
        data.point.y = click["y"]
        click = None
    else:   
        data.point.x = click["x"]
        data.point.y = click["y"]
        click["reported"] = True
        data.state = lv.INDEV_STATE.PR
    return False
    
# start listening for http connections
def start(port=80):
    if espidf.mdns_init() == 0 and espidf.mdns_hostname_set('littleblockly') == 0:
        print("mdns: littleblockly.local")

    # setup input driver to send click events
    drv = lv.indev_drv_t()
    drv.init()
    drv.type = lv.INDEV_TYPE.POINTER
    drv.read_cb = input_callback
    drv.register()    

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    addr = socket.getaddrinfo("0.0.0.0", port)[0][4]
    
    server_socket.bind(addr)
    server_socket.listen(5)
    server_socket.setsockopt(socket.SOL_SOCKET, 20, accept_http_connect)  # <- ????
    
    for i in (network.AP_IF, network.STA_IF):
        wlan = network.WLAN(i)
        if wlan.active():
            print("Web server started on {}:{}".format(wlan.ifconfig()[0], port))

    return server_socket
