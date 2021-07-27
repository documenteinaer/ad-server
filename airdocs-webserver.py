#!/usr/bin/env python

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
from os import listdir
import os.path
from os.path import isfile, join
import shelve
from compare_signatures import *

db_name = "airdocs"

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
        db = shelve.open(db_name, writeback=True)
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        parsed = json.loads(post_body)
#         print_json(parsed) # here we display the whole message
#         write_json_to_file(parsed["fingerprints"]) #write only fingerprints to file
        self._set_headers()

        # Test
        if (parsed["type"] == "0"):
            self.wfile.write(self._html("Successful Testing"))
            print(parsed["fingerprints"])

        # Add document to Database
        if (parsed["type"] == "1"):
            #TODO - do something with the received file - parsed["documentURL"] & fingerprints - parsed["fingerprints"]
            self.wfile.write(self._html("Successful Sending"))
            signature = parsed["fingerprints"]
            signature = signature[list(signature.keys())[0]]
            document = parsed["document"]
            try:
                db["document"+str(db['count'])] = {}
                db["document"+str(db['count'])]["document"] = document
#                 for c in signature:
#                     precalculate_fingerprints(signature[c])
#                     print(signature)
                db["document"+str(db['count'])]["signature"] = signature
            finally:
                db["count"] += 1

        # Search for documents
        if (parsed["type"] == "2"):
            #TODO - use fingerprints - parsed["fingerprints"] to search for file and return the url here
            response = {}
            self.wfile.write(self._html("New document URL here111"))
            q_signature = parsed["fingerprints"]
            q_signature = q_signature[list(q_signature.keys())[0]]

            precalculate_fingerprints(q_signature)
            for d in db:
                if "document" in d:
                    precalculate_fingerprints(db[d]["signature"])
                    response[d] = {"similarity": compare_fingerprints(q_signature, db[d]["signature"]),
                                 "document" : db[d]["document"],
                                 "description": db[d]["signature"]["comment"]}

            print(response)
            self.wfile.write(json.dumps(response).encode(encoding='utf_8'))
        db.close()



def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000, filename=None, dir=None, config=None):
    db = shelve.open(db_name, writeback = True)
    if not 'count' in db:
        db['count'] = 0
        db.close()
    if filename!=None:
        open_json(filename)
    if dir!=None:
        open_dir(dir)
    if config!=None:
        open_config(config)
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print("Starting httpd server on {addr}:{port}")
    httpd.serve_forever()

def get_time():
    now = datetime.now()
    dt_string = now.strftime("%d-%m-%Y_%H-%M-%S")
    print("date and time =", dt_string)
    return dt_string+".json"

def open_json(filename):
    extension = os.path.splitext(filename)[1][1:]
    if (extension == "json"):
        f = open(filename,'r')
        data = json.load(f)
        print_json(data)
        f.close()

def print_json(data):
    print(json.dumps(data, indent=4, sort_keys=False))
    print("Message type: ", data["type"])

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
    run(addr=args.listen, port=args.port, filename=args.file, dir=args.dir, config=args.config)
