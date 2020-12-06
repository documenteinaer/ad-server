#!/usr/bin/env python
"""
Very simple HTTP server in python (Updated for Python 3.7)

Usage:

    ./dummy-web-server.py -h
    ./dummy-web-server.py -l localhost -p 8000

Send a GET request:

    curl http://localhost:8000

Send a HEAD request:

    curl -I http://localhost:8000

Send a POST request:

    curl -d "foo=bar&bin=baz" http://localhost:8000

"""
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime


class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        """This just generates an HTML document that includes `message`
        in the body. Override, or re-write this do do more interesting stuff.

        """
        content = f"<html><body><h1>{message}</h1></body></html>"
        return content.encode("utf8")  # NOTE: must return a bytes object!

    def do_GET(self):
        self._set_headers()
        self.wfile.write(self._html("hi!"))

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        parsed = json.loads(post_body)
        print(json.dumps(parsed, indent=4, sort_keys=False))
        with open(get_time(), 'w') as json_file:
                json.dump(parsed, json_file, indent=4)
        self._set_headers()
        self.wfile.write(self._html("Successful POST"))


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()

def get_time():
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H-%M-%S")
    print("date and time =", dt_string)
    return dt_string+".json"


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l",
        "--listen",
        default="localhost",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)
