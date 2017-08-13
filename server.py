from threading import Thread

from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

import os
import netifaces as ni

SERVER_PORT = 8080
OUTPUT_AUDIO_NAME = 'sonos-assistant.wav'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
RESOURCES_DIR = "resources"
OUTPUT_AUDIO_FILE = RESOURCES_DIR + '/' + OUTPUT_AUDIO_NAME
LOCAL_AUDIO_FILE = ROOT_PATH + '/' + OUTPUT_AUDIO_FILE


def get_ip_address(ifname='en0'):
    """Return local IP address"""
    return ni.ifaddresses(ifname)[ni.AF_INET][0]['addr']


def get_path_for_file(file_name):
    return 'http://{}:{}/{}'.format(get_ip_address(), SERVER_PORT, file_name)

SERVER_AUDIO_FILE = get_path_for_file(OUTPUT_AUDIO_FILE)


class HttpServer(Thread):
    """A simple HTTP Server in its own thread"""

    def __init__(self, port):
        super(HttpServer, self).__init__()
        self.daemon = True
        handler = SimpleHTTPRequestHandler
        self.httpd = TCPServer(("", port), handler)

    def run(self):
        """Start the server"""
        print('Start HTTP server')
        self.httpd.serve_forever()

    def stop(self):
        """Stop the server"""
        print('Stop HTTP server')
        self.httpd.socket.close()
