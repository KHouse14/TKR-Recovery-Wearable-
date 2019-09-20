import os
import board
import busio
from digitalio import DigitalInOut
import neopixel
#from code import spi

from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_wifimanager as wifimanager
import adafruit_esp32spi.adafruit_esp32spi_wsgiserver as server

from secrets import secrets

try:
    import json as json_module
except ImportError:
    import ujson as json_module

print("Loading ESP32 SPI web server...")

# SAM32 board ESP32 Setup
dtr = DigitalInOut(board.DTR)
esp32_cs = DigitalInOut(board.TMS) #GPIO14
esp32_ready = DigitalInOut(board.TCK) #GPIO13
esp32_reset = DigitalInOut(board.RTS)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset, gpio0_pin=dtr, debug=False)

status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
wifi.connect()

class SimpleWSGIApplication:
    INDEX = "/index.html"
    CHUNK_SIZE = 8912

    def __init__(self, static_dir=None):
        self._listeners = {}
        self._start_response = None
        self._static = static_dir
        if self._static:
            self._static_files = ["/" + file for file in os.listdir(self._static)]

    def __call__(self, environ, start_response):

        self._start_response = start_response
        status = ""
        headers = []
        resp_data = []

        key = self._get_listener_key(environ["REQUEST_METHOD"].lower(), environ["PATH_INFO"])
        if key in self._listeners:
            status, headers, resp_data = self._listeners[key](environ)
        if environ["REQUEST_METHOD"].lower() == "get" and self._static:
            path = environ["PATH_INFO"]
            if path in self._static_files:
                status, headers, resp_data = self.serve_file(path, directory=self._static)
            elif path == "/" and self.INDEX in self._static_files:
                status, headers, resp_data = self.serve_file(self.INDEX, directory=self._static)

        self._start_response(status, headers)
        return resp_data

    def on(self, method, path, request_handler):
        """
        Register a Request Handler for a particular HTTP method and path.
        request_handler will be called whenever a matching HTTP request is received.

        request_handler should accept the following args:
            (Dict environ)
        request_handler should return a tuple in the shape of:
            (status, header_list, data_iterable)

        :param str method: the method of the HTTP request
        :param str path: the path of the HTTP request
        :param func request_handler: the function to call
        """
        self._listeners[self._get_listener_key(method, path)] = request_handler

    def serve_file(self, file_path, directory=None):
        status = "200 OK"
        headers = [("Content-Type", self._get_content_type(file_path))]

        full_path = file_path if not directory else directory + file_path
        def resp_iter():
            with open(full_path, 'rb') as file:
                while True:
                    chunk = file.read(self.CHUNK_SIZE)
                    if chunk:
                        yield chunk
                    else:
                        break

        return (status, headers, resp_iter())

    def _log_environ(self, environ): # pylint: disable=no-self-use
        print("environ map:")
        for name, value in environ.items():
            print(name, value)

    def _get_listener_key(self, method, path): # pylint: disable=no-self-use
        return "{0}|{1}".format(method.lower(), path)

    def _get_content_type(self, file): # pylint: disable=no-self-use
        ext = file.split('.')[-1]
        if ext in ("html", "htm"):
            return "text/html"
        if ext == "js":
            return "application/javascript"
        if ext == "css":
            return "text/css"
        if ext in ("jpg", "jpeg"):
            return "image/jpeg"
        if ext == "png":
            return "image/png"
        return "text/plain"

static = "/static"
web_app = SimpleWSGIApplication(static_dir=static)

server.set_interface(esp)
wsgiServer = server.WSGIServer(80, application=web_app)

print("Open this IP in your browser: ", esp.pretty_ip(esp.ip_address))
wsgiServer.start()

def getFile(path):
    return web_app.serve_file("static/" + path)

def register(request, path, fn):
    web_app.on(request, path, fn)

def poll():
    wsgiServer.update_poll()