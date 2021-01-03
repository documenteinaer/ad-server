#!/usr/bin/env python

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
from os import listdir
import os.path
from os.path import isfile, join


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
        print_json(parsed)
        write_json_to_file(parsed)
        self._set_headers()
        self.wfile.write(self._html("Successful POST"))


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000, file=None, dir=None, config=None):
    if file!=None:
        open_json(file)
    if dir!=None:
        open_dir(dir)
    if config!=None:
        open_config(config)
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()

def get_time():
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H-%M-%S")
    print("date and time =", dt_string)
    return dt_string+".json"

def open_json(file):
    extension = os.path.splitext(file)[1][1:]
    if (extension == "json"):
        f = open(file,'r')
        data = json.load(f)
        print_json(data)
        f.close()

def print_json(data):
    print(json.dumps(data, indent=4, sort_keys=False))

def write_json_to_file(data):
    with open(get_time(), 'w') as json_file:
                json.dump(data, json_file, indent=4)

def open_dir(mypath):
    files = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    for file in files:
        print(file)
        filepath = mypath + "/" + file
        open_json(filepath)

def open_config(config):
    with open(config, 'r') as fp:
        line = fp.readline()
        while line:
            print("Reading from directory: "+line.strip())
            open_dir(line.strip())
            line = fp.readline()

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
    parser.add_argument(
        "-f",
        "--file",
        help="Specify the json file",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--dir",
        help="Specify directory with json files",
        required=False,
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Specify config file",
        required=False,
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port, file=args.file, dir=args.dir, config=args.config)
