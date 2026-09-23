import socketpool
import wifi
from adafruit_httpserver import GET, POST, Request, Response, Server
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import adafruit_ducky

AP_SSID = "jaaniedasi"
AP_PASSWORD = "Kur1Mur1Ur1nURR"
FORM_HTML_TEMPLATE = """
<html lang="en">
    <head>
        <title>PWN!</title>
    </head>
    <body>
        <h2>Write your duckyscript here!</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <label for="file">Choose a file:</label>
                <input type="file" id="file" name="file"><br><br>
            <input type="submit" value="Upload">
          </form>
    </body>
</html>
"""

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)

try:
    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, root_path="/upload", debug=True)
    print("Creating access point...")
    wifi.radio.start_ap(ssid=AP_SSID, password=AP_PASSWORD)
    print(f"Created access point {AP_SSID}")
except Exception as e:
    print(e)

@server.route("/upload", [GET, POST])
def form(request: Request):
    if request.method == POST:
        try:
            ducky_file = request.form_data.files.get("file")
            if ducky_file:
                with open("ducky.txt", "wb") as f:
                    f.write(ducky_file.content_bytes)
                execute_script("ducky.txt")
        except Exception as e:
            print(e)

    return Response(
        request,
        FORM_HTML_TEMPLATE.format(
            done_value=(
                "Sent!"
                if request.method == POST
                else ""
            ),
        ),
        content_type="text/html",
    )

def execute_script(filename):
    duck = adafruit_ducky.Ducky(filename, keyboard, keyboard_layout)
    not_yet = True
    while not_yet:
        not_yet = duck.loop()

try:
    execute_script("ducky.txt")
    server.serve_forever(str(wifi.radio.ipv4_address_ap))
except Exception as e:
    print(e)