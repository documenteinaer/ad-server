#!/usr/bin/env python

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler
from http import HTTPStatus
import json, base64
from datetime import datetime
from os import listdir
import os.path
from os.path import isfile, join
import shelve
from compare_signatures import *
import zlib
import uuid 
import shutil
from signal import *
import sys
import socket, os
from socketserver import BaseServer
# from SimpleHTTPServer import SimpleHTTPRequestHandler
from OpenSSL import SSL
import ssl
import string

import requests
from requests.exceptions import HTTPError


db_name = "airdocs"
global has_db_been_closed
db = None

class S(BaseHTTPRequestHandler):
    def _set_headers(self, code):
        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        """This just generates an HTML document that includes `message`
        in the body. Override, or re-write this do do more interesting stuff.

        """
        content = f"<html><body><h1>{message}</h1></body></html>"
        return content.encode("utf8")  # NOTE: must return a bytes object!

    def do_GET(self):
        self._set_headers(HTTPStatus.OK)
        self.wfile.write(self._html("hi!"))

    def do_HEAD(self):
        self._set_headers(HTTPStatus.OK)

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

        # Test
        if (parsed["type"] == "TEST"):
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(self._html("Successful Testing"))
            print(parsed["fingerprints"])

        # Delete 1 file
        if (parsed["type"] == "DELFILE"):
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(self._html("Successful Deleting"))
            id = parsed["id"]
            devId = db[id]["signature"]["devId"]
            if (devId == parsed["devid"]):
                print("deleting " + id)
                del db[id]
                full_path = "storage/" + id + "/"
                if os.path.exists(full_path):
                    try:
                        shutil.rmtree(full_path)
                    except OSError as e:
                        print("Error: %s - %s." % (e.filename, e.strerror))

        # Delete all files from a certain device
        if (parsed["type"] == "DELALL"):
            self._set_headers(HTTPStatus.OK)
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
            # print("parsed: %s" % parsed)
            signature = parsed["fingerprints"]
            # print("signature: %s" % signature)
            filetype = parsed["filetype"]
            # print("filetype: %s" % filetype)

            signature = signature[list(signature.keys())[0]]
            document = os.path.basename(parsed["document"])
            key = self.docname(signature)
            if not os.path.exists("storage"):
                os.makedirs("storage")
            if ('file' in parsed):
                # os.makedirs("storage/" + key)
                # doc_name = "storage/"+ key + "/" + document
                # with open(doc_name, "wb") as fp:
                #     content = base64.b64decode(parsed['file']) # fails on invalid file: "\/9j\/4AAQSkZJRgABAQAAAQABAAD\/CxABn13\/W" -> search, then post, then anything else
                #     fp.write(content)
                try: # check whether or not the file is in the correct format - otherwise an exception may occur and break the application
                    content = base64.b64decode(parsed['file'])
                    # print(content)
                except Exception as e:
                    return cleanup_db(self, db, str(e))
                else:
                    os.makedirs("storage/" + key)
                    doc_name = "storage/"+ key + "/" + document
                    with open(doc_name, "wb") as fp:
                        fp.write(content)
            try:
                db[key] = {"document": document, "filetype": filetype, "signature": signature}
                # print("db[%s]: " % key)
                # print(db[key])
                # db["document"+str(db['count'])] = {"document": document, "signature": signature}
            finally:
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(self._html("Successful Sending"))
                db["count"] += 1

                # TODO: send to IndoorAtlas {coordinates, key, documentname }
                # # indoorAtlasURL = 'https://positioning-api.indooratlas.com/v1/venues/4a3a0540-9fca-11ed-912a-d149562ef888?key=01e2ffb8-fba6-4ef7-a9da-deabc075e063'
                # indoorAtlasURL = 'https://app.indooratlas.com/web-api/venue-meta/4a3a0540-9fca-11ed-912a-d149562ef888/geofences'
                # accessToken = "JWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlrZXkiOnsiaWQiOiIwYjQ3Y2QxOC0xZGE5LTQzZDctYjQ1Mi00ZjQwNTBkNzM2ODQifSwidXNlciI6eyJpZCI6ImE1ZmI2MzViLTlkOGMtNDQyNS1hOWZhLWI0Yjg1ZmIyMWQ3MiIsInVzZXJuYW1lIjoidmxhZGFsZXgwMiIsImVtYWlsIjoiY2F0YW5vaXUudmxhZEB5YWhvby5jb20iLCJ0b3NWZXJzaW9uIjozfSwiaWF0IjoxNjc4OTk2NTk4LCJleHAiOjE2NzkwODI5OTh9.A79fmQ4Sz48WLXKoGuPXUpz2_v2USpwnzGICX9gNPn0" # TODO: find a way to generate this
                # response = requests.get(indoorAtlasURL, headers={'Authorization': accessToken, 'Content-Type': 'application/json;charset=UTF-8'})

                # jsonResponse = response.json()

                # payload_features = jsonResponse["features"]

                # indoorAtlasDefault  = {
                #     "AR": {
                #         "image": {
                #             "name": "AirDoc",
                #             "sha256": "2df6a3c13587b2dff4e07eb053a26d8329874e67c3224e34644d86a3740d9a74",
                #             "url": "https://ida-poi-images-prod.s3.eu-west-1.amazonaws.com/a5fb635b-9d8c-4425-a9fa-b4b85fb21d72/images/2df6a3c13587b2dff4e07eb053a26d8329874e67c3224e34644d86a3740d9a74"
                #         }
                #     }
                # }

                # characters = string.digits + 'abcdef'
                # id_1 = ''.join(random.choice(characters) for i in range(8))
                # id_2 = ''.join(random.choice(characters) for i in range(4))
                # id_3 = ''.join(random.choice(characters) for i in range(4))
                # id_4 = ''.join(random.choice(characters) for i in range(4))
                # id_5 = ''.join(random.choice(characters) for i in range(12))

                # new_feature = {
                #     "type": "Feature",
                #     # "id": id_1+'-'+id_2+'-'+id_3+'-'+id_4+'-'+id_5, # TODO
                #     "id": "0baaed80-a0a6-11ed"+'-'+id_4+'-'+id_5, # TODO
                #     "properties": {
                #         "floor": signature["floor"],
                #         "description": document,
                #         "payload": {
                #             "IndoorAtlas": indoorAtlasDefault,
                #             "AirdocsKey": key
                #         }
                #     },
                #     "geometry": {
                #         "type": "Point",
                #         "coordinates": [
                #             signature["longitude"], # TODO
                #             signature["latitude"] # TODO
                #         ]
                #     }
                # }

                # payload_features.append(new_feature) 
                # payload = {
                #     "type": "FeatureCollection",
                #     "features": payload_features
                # }
                # # print("PAYLOAD:")
                # json_string = json.dumps(payload) 
                # # print(json_string)

                # response = requests.put(indoorAtlasURL, headers={'Authorization': accessToken, 'Content-Type': 'application/json;charset=UTF-8'}, data=json_string)
                
                # print("Status Code", response.status_code)
                # print("JSON Response ", response.json())


        # Search for documents
        if (parsed["type"] == "SEARCH"):
            self._set_headers(HTTPStatus.OK)
            #TODO - use fingerprints - parsed["fingerprints"] to search for file and return the url here
            response = []
            #self.wfile.write(self._html("New document URL here111"))
            q_signature = parsed["fingerprints"]
            q_signature = q_signature[list(q_signature.keys())[0]]
            q_sim_threshold = float(parsed["threshold"])

            if q_sim_threshold > 1: # this should not be included.
                q_sim_threshold = 1

            precalculate_fingerprints(q_signature)
            for d in db:
                if d != "count":
                    precalculate_fingerprints(db[d]["signature"])
                    similarity = compare_fingerprints(q_signature, db[d]["signature"])
                    print("similarity", similarity)
                    if similarity < q_sim_threshold:
                        document = db[d]["document"]
                        latitude = db[d]["signature"]["latitude"]
                        longitude = db[d]["signature"]["longitude"]
                        altitude = 0
                        if "altitude" in db[d]["signature"]:
                            altitude = db[d]["signature"]["altitude"]

                        print(altitude)
                        description = db[d]["signature"]["comment"]
                        # -> devID? maybe roles? TODO: Discussions 
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
                                     "latitude": latitude,
                                     "longitude": longitude,
                                     "altitude": altitude,
                                     "file": file_string,
                                     "filetype": filetype})
                        else:
                            response.append({"similarity": similarity,
                                     "id" : d,
                                     "document" : document,
                                     "description": description,
                                     "latitude": latitude,
                                     "longitude": longitude,
                                     "altitude": altitude,
                                     "filetype": filetype})

            response = sorted(response, key = lambda i: i["similarity"])
            # print(response)
            self.wfile.write(json.dumps(response).encode(encoding='utf_8'))
        cleanup_db(self, db, "")


def cleanup_db(self, db, err_msg):
    if len(err_msg) > 0:
        self.send_response(HTTPStatus.BAD_REQUEST)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(self._html("Cannot process request data: " + err_msg))
    global has_db_been_closed
    db.close()
    print("", flush=True) # h@ck! for docker not printing stdout
    has_db_been_closed = True


# def open_db(db_name, writeback = True):
#     global has_db_been_closed
#     global db
#     if has_db_been_closed:
#         db = shelve.open(db_name, writeback)
#     return db

def handler(signal_received, frame):
   # Handle any cleanup here
   global has_db_been_closed
   global db
   print('Got signal %d. Exiting gracefully.' % (signal_received))
   if db is not None and has_db_been_closed == False:
       db.close()
       has_db_been_closed = True
   exit(1)

# class SecureHTTPServer(HTTPServer):
#     def __init__(self, server_address, HandlerClass):
#         BaseServer.__init__(self, server_address, HandlerClass)
#         ctx = SSL.Context(SSL.SSLv23_METHOD)
#         #server.pem's location (containing the server private key and
#         #the server certificate).
#         fpem = './server.pem'
#         ctx.use_privatekey_file (fpem)
#         ctx.use_certificate_file(fpem)
#         self.socket = SSL.Connection(ctx, socket.socket(self.address_family,
#                                                         self.socket_type))
#         self.server_bind()
#         self.server_activate()
    
# class SecureHTTPRequestHandler(BaseHTTPRequestHandler):
#     def setup(self):
#         self.connection = self.request
#         self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
#         self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000, filename=None, dir=None, config=None, cert=None):
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
    # server_address = ('', 443)
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    # httpd = HTTPServer(('localhost', 1443), SimpleHTTPRequestHandler)
    # sslctx = ssl.SSLContext()
    # sslctx.check_hostname = False # If set to True, only the hostname that matches the certificate will be accepted
    # sslctx.load_cert_chain(certfile='certificate.pem', keyfile="private.pem")
    # httpd.socket = sslctx.wrap_socket(httpd.socket, server_side=True)

    # httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    # TODO: if TLS -> cert as arg
    if cert!=None:
        print("Using cert", cert)
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=cert, server_side=True)

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
        "--cert",
        help="Specify the TLS cert file",
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
    run(addr=args.listen, port=args.port, filename=args.file, dir=args.dir, config=args.config, cert=args.cert)
