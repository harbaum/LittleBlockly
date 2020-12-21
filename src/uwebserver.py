import socket
import network
import espidf

def check4file(fname):
    try:
        open(fname, "r")
        return True
    except:
        return False

def do_POST(hdr, s):        
    boundary = None
    s_file = s.makefile('rwb', 0)
    for l in hdr:
        parts = l.split(':', 1)
        if len(parts) == 2 and parts[0].strip() == "Content-Type":
            ctype =  parts[1].split(';')
            if len(ctype) == 2:
                for ct in ctype:                            
                    ctp = ct.split('=')
                    if len(ctp) == 2:
                        if ctp[0].lower().strip() == "boundary":
                            boundary = "--" + ctp[1].strip()

    print("Boundary", boundary);

    if not boundary:
        print("No boundary");
        return

    # states:
    # 0 - wait for start boundary
    # 1 - wait for header end empty line
    # 2 - data phase, wait for end boundary
    # 3 - done
    state = 0
    fp = None
    while state < 3:
        line = s_file.readline()
        if not line:
            print("PREMATURE END!")
            break

        if state == 1 and line == b'\r\n':
            print("DATA BEGIN");
            state = state + 1
        else:
            try:
                line = line.decode('utf-8')
            except:
                # we cannot decode this. May be binary data. We don't care ...
                print("Trouble with line",str(line))
                return
                
            sline = line.strip()

            if sline.startswith(boundary):
                print("START/END");
                state = state + 1
            elif state == 1:
                # in state one parse the header lines for e.g. the
                # file name
                
                # Content-Disposition: form-data; name="file"; filename="run_simple.py"
                cparts = sline.split(":", 1)
                if len(cparts) == 2 and cparts[0].strip() == "Content-Disposition":
                    dparts = cparts[1].split(';')
                    for dpart in dparts:
                        dp = dpart.split("=", 1)
                        if len(dp) == 2 and dp[0].strip() == "filename":
                            filename = dp[1].strip("\" ")
                            print("writing to", filename)
                            fp = open("/apps/"+filename, "w")
                                        
                print("HDR:", line.strip())
            elif state == 2:
                print(line.rstrip("\n"))
                if fp: fp.write(line)

    if fp:
        fp.close()

def accept_http_connect(http_server):
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
        "js": "application/javascript"
    }
    
    client_socket, remote_addr = http_server.accept()
    print("Http connection from:", remote_addr)
    client_socket.setblocking(False)
    client_socket.settimeout(2)

    client_socket_file = client_socket.makefile('rwb', 0)
    data = []
    while True:
        try:
            line = client_socket_file.readline()
        except Exception as e:
            print("read failed:", e);
            client_socket.close()
            return
            
        if not line or line == b'\r\n':
            break

        data.append(line.decode('utf-8').strip())

    print("Request:");
    for l in data:
        print("   ", l)
    
    if len(data) == 0:
        print("empty request??")
        client_socket.close()
        return
    
    items = data[0].split(' ');
    if items[0] == "POST":
        do_POST(data, client_socket)

        client_socket.send('HTTP/1.1 200 OK\n')
        client_socket.send('Content-Type: text/html\n')                
        client_socket.send('Connection: close\n\n')
        client_socket.send("<html>OK</html>")            

        client_socket.close()
        return
            
    if items[0] == "GET":
        fname = "/html"+items[1]
        if fname[-1] == '/':
            fname = fname + "index.html"

        # check if file exists. May be compressed ...
        fok = False
        compressed = False
        if check4file(fname):
            fok = True
        if check4file(fname+".gz"):
            fok = True
            compressed = True

        if fok:
            client_socket.send('HTTP/1.1 200 OK\n')
            parts = fname.split('.')
            ext = parts[len(parts)-1]
            if ext in CONTENT_TYPES:
                mimetype = CONTENT_TYPES[ext]
            else:
                mimetype = "application/octet-stream"
            client_socket.send('Content-Type: '+mimetype+'\n')                
        else:
            print("404: Not found");
            client_socket.send('HTTP/1.1 404 FILE NOT FOUND\n')
            client_socket.send('Content-Type: text/html\n')                
            client_socket.send('Connection: close\n\n')
            client_socket.send("<html><h1>404 Error</h1></html>")            
            client_socket.close()
            return

        # check if gzipped file exists and use that if present
        if compressed:
            fname = fname + ".gz"
            client_socket.send('Content-Encoding: gzip\n')

        client_socket.send('Connection: close\n\n')
        print("Sending", fname);
    
        try:
            f = open(fname, "rb")
            while True:
                data = f.read(32*1024)
                if not data:
                    print("file done", remote_addr);
                    break

                print("Sending", len(data), " bytes to", remote_addr);
                client_socket.send(data)
                
        except Exception as e:
            print("Sending file failed", e);
            client_socket.send("<html><h1>Error</h1></html>")
        
    client_socket.close()
    print("tx done", remote_addr);
    
# start listening for http connections on port 80
def start(port=80):
    if espidf.mdns_init() == 0 and espidf.mdns_hostname_set('littleblockly') == 0:
        print("mdns: littleblockly.local")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    addr = socket.getaddrinfo("0.0.0.0", port)[0][4]
    
    server_socket.bind(addr)
    server_socket.listen(5)
    server_socket.setsockopt(socket.SOL_SOCKET, 20, accept_http_connect)
    
    for i in (network.AP_IF, network.STA_IF):
        wlan = network.WLAN(i)
        if wlan.active():
            print("Web server started on {}:{}".format(wlan.ifconfig()[0], port))
