import time
import board
import busio
import socketpool
import wifi
from adafruit_httpserver import GET, POST, Request, Response, Server, REQUEST_HANDLED_RESPONSE_SENT

class Lora:
    def __init__(self, tx_pin, rx_pin, baudrate, peer=77, timeout=30):
        self.uart = busio.UART(tx=tx_pin, rx=rx_pin, baudrate=baudrate)
        self.seq = 0
        self.peer = peer
        self.timeout = timeout
        self.band=868600000
        self.adr=77
        self.network_id=10

        # init that shit
        self.uart.write(bytes("AT+NOIDEA\r\n", "ascii"))
        time.sleep(3)
        self.uart.write(bytes(f"AT+BAND={self.band}\r\n", "ascii"))
        time.sleep(3)
        self.uart.write(bytes(f"AT+ADDRESS={self.adr}\r\n", "ascii"))
        time.sleep(3)
        self.uart.write(bytes(f"AT+NETWORKID={self.network_id}\r\n", "ascii"))
        time.sleep(3)

        # clear the queue
        while self.uart.readline():
            pass

    def receive(self):
        msg = self.uart.readline()
        if msg:
            if msg.startswith(b"+RCV"):
                return msg.decode("ascii").split(",")[2].strip()

    def send(self, msg, adr=88):
        acked_msg = f"{self.seq}#{msg}"
        print(f"[ ? ] Sending line: {acked_msg}")
        self.uart.write(bytes(f"AT+SEND={adr},{len(acked_msg)},{acked_msg}\r\n", "ascii"))
        start = time.monotonic()
        while time.monotonic() - start < self.timeout:
            resp = self.receive()
            if resp:
                if resp.startswith(str(self.seq)):
                    print(f"[ + ] ACK received for {acked_msg}")
                    return True
                else:
                    time.sleep(0.1)
        return False

AP_SSID = "jaaniedasi"
AP_PASSWORD = "Kur1Mur1Ur1nURR"
FORM_HTML_TEMPLATE = """
<html lang="en">
    <head>
        <title>PWN!</title>
    </head>
    <body>
        <h2>Upload your duckyscript here!</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <label for="file">Choose a file:</label>
            <input type="file" id="file" name="file"><br><br>
            <input type="submit" value="Upload">
        </form>
        <p>{done_value}</p>
    </body>
</html>
"""

try:
    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, root_path="/upload", debug=True)
    print("[ ? ] Creating access point...")
    wifi.radio.start_ap(ssid=AP_SSID, password=AP_PASSWORD)
    print(f"[ + ] Created access point {AP_SSID}")
    server.start(str(wifi.radio.ipv4_address_ap))
    lora = Lora(tx_pin=board.GP16, rx_pin=board.GP13, baudrate=115200)
except Exception as e:
    print(e)

ducky_file = None

def process_file():
    try:
        if ducky_file:
            cmds = ducky_file.content_bytes.decode("ascii").splitlines()
            cmds.append("DNE")
            for d in cmds:
                acked = False    
                while not acked:
                    acked = lora.send(d.strip())
                    if not acked:
                        print("[ - ] Trying again ...")
                lora.seq = lora.seq + 1
                time.sleep(2)
            print("[ +++ ] Script sent! :3\n")
        lora.seq = 0
    except Exception as e:
        print(e)

# todo: return the response and execute lora shit async?
@server.route("/upload", [GET, POST])
def form(request: Request):
    global ducky_file
    if request.method == POST:
        try:
            ducky_file = request.form_data.files.get("file")
        except Exception as e:
            print(e)
    return Response(
        request,
        FORM_HTML_TEMPLATE.format(
            done_value=(
                "Got it! Now processing!"
                if request.method == POST
                else ""
            ),
        ),
        content_type="text/html",
    )

while True:
    try:
        pool_result = server.poll()
        if pool_result == REQUEST_HANDLED_RESPONSE_SENT:
            process_file()
    except Exception as e:
        print(e)
        continue
