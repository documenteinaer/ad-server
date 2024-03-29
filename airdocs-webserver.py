#!/usr/bin/env python

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, base64
from datetime import datetime
from os import listdir
import os.path
from os.path import isfile, join
import shelve
from compare_signatures import *
from compare_signatures_ble import *
import zlib
import uuid 
import shutil
import copy
from signal import *

db_name = "airdocs"
global has_db_been_closed
db = None

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

    def docname(self, signature):
        # CRC32 produces 32 bit of the entire signature(devID, wifi, gps, ble)
        crc = zlib.crc32(str(signature).encode())
        # CRC is padded with zeros in the front, base64 encoded, last 8 characters taken   
        key = base64.b64encode(bytes(str(crc).rjust(8, '0'), 'ascii')).decode().strip('=+/')[-8:]
        # 2 random characters (time based)
        key = key + str(uuid.uuid4())[0:2]
        return key
        
    def do_POST(self):
        global has_db_been_closed
        global db
        if has_db_been_closed:
            db = shelve.open(db_name, writeback=True)
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        parsed = json.loads(post_body)
#         print_json(parsed) # here we display the whole message
#         write_json_to_file(parsed["fingerprints"]) #write only fingerprints to file
        self._set_headers()

        # Test
        if (parsed["type"] == "TEST"):
            self.wfile.write(self._html("Successful Testing"))
            print(parsed["fingerprints"])

        # Delete 1 file
        if (parsed["type"] == "DELFILE"):
            self.wfile.write(self._html("Successful Deleting"))
            id = parsed["id"]
            devId = db[id]["signature"]["devId"]
            if (devId == parsed["devid"]):
                print("deleting " + id)
                try:
                    del db[id]
                finally:
                    db["count"] -= 1
                full_path = "storage/" + id + "/"
                if os.path.exists(full_path):
                    try:
                        shutil.rmtree(full_path)
                    except OSError as e:
                        print("Error: %s - %s." % (e.filename, e.strerror))

        # Delete all files from a certain device
        if (parsed["type"] == "DELALL"):
            self.wfile.write(self._html("Successful Deleting"))
            for d in db:
                if d != "count":
                    devId = db[d]["signature"]["devId"]
                    if (devId == parsed["devid"]):
                        print("deleting " + d)
                        del db[d]
                        full_path = "storage/" + d + "/"
                        if os.path.exists(full_path):
                            try:
                                shutil.rmtree(full_path)
                            except OSError as e:
                                print("Error: %s - %s." % (e.filename, e.strerror))


        # Add document to Database
        if (parsed["type"] == "POST"):
            #TODO - do something with the received file - parsed["documentURL"] & fingerprints - parsed["fingerprints"]
            self.wfile.write(self._html("Successful Sending"))
            signature = parsed["fingerprints"]
            filetype = parsed["filetype"]
            signature = signature[list(signature.keys())[0]]
            document = os.path.basename(parsed["document"])
            key = self.docname(signature)
            if not os.path.exists("storage"):
                os.makedirs("storage")
            if ('file' in parsed):
                os.makedirs("storage/" + key)
                doc_name = "storage/"+ key + "/" + document
                with open(doc_name, "wb") as fp:
                    content = base64.b64decode(parsed['file'])
                    fp.write(content)     
            try:
                db[key] = {"document": document, "filetype": filetype, "signature": signature}
                # db["document"+str(db['count'])] = {"document": document, "signature": signature}
            finally:
                db["count"] += 1

        # Search for documents
        if (parsed["type"] == "SEARCH"):
            #TODO - use fingerprints - parsed["fingerprints"] to search for file and return the url here
            response = []
            #self.wfile.write(self._html("New document URL here111"))
            q_signature = parsed["fingerprints"]
            q_signature = q_signature[list(q_signature.keys())[0]]
            q_sim_threshold = float(parsed["threshold"])

            #if q_sim_threshold > 1:
            #    q_sim_threshold = 1

            #print(q_signature)
            

            #precalculate_fingerprints_ble(q_signature)
            precalculate_fingerprints(q_signature)
            for d in db:
                if d != "count":
                    #print("----------")
                    db_signature = copy.deepcopy(db[d]["signature"])
                    #print(db_signature["comment"])
                    #precalculate_fingerprints_ble(db_signature)
                    #similarity = compare_fingerprints_ble(q_signature, db_signature)
                    precalculate_fingerprints(db_signature)
                    similarity = compare_fingerprints(q_signature, db_signature)
                    #print(similarity)
                    if similarity <= q_sim_threshold:
                        document = db[d]["document"]
                        description = db[d]["signature"]["comment"]
                        filetype = db[d]["filetype"]
                        full_path = "storage/" + d + "/" + document
                        if os.path.exists(full_path):
                            with open(full_path, "rb") as fp:
                                file_data = fp.read()
                                aux = base64.b64encode(file_data);
                                file_string = aux.decode('utf-8')
                                response.append({"similarity": similarity,
                                     "id" : d,
                                     "document" : document,
                                     "description": description,
                                     "file": file_string,
                                     "filetype": filetype})
                        else:
                            response.append({"similarity": similarity,
                                     "id" : d,
                                     "document" : document,
                                     "description": description,
                                     "filetype": filetype})

            response = sorted(response, key = lambda i: i["similarity"])
            #print(response)
            self.wfile.write(json.dumps(response).encode(encoding='utf_8'))
        cleanup_db(self, db, "")


def cleanup_db(self, db, err_msg):
    #if len(err_msg) > 0:
    #    self.send_response(HTTPStatus.BAD_REQUEST)
    #    self.send_header("Content-type", "text/html")
    #    self.end_headers()
    #    self.wfile.write(self._html("Cannot process request data: " + err_msg))
    global has_db_been_closed
    db.close()
    #print("", flush=True) # h@ck! for docker not printing stdout
    has_db_been_closed = True


def handler(signal_received, frame):
   # Handle any cleanup here
   global has_db_been_closed
   global db
   print('Got signal %d. Exiting gracefully.' % (signal_received))
   if db is not None and has_db_been_closed == False:
       db.close()
       has_db_been_closed = True
   exit(1)

def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000, filename=None, dir=None, config=None):
    global db
    global has_db_been_closed
    has_db_been_closed  = False
    db = shelve.open(db_name, writeback = True)

    if not 'count' in db:
        db['count'] = 0
        db.close()
        has_db_been_closed = True

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

    signal(SIGINT, handler)
    signal(SIGTERM, handler)

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
