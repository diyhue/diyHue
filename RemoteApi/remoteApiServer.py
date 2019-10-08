#!/usr/bin/python3
import argparse
import json
import logging
import os
import ssl
import sys
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from pprint import pprint
from time import sleep

bridges = {}
clients = []
discovery = {}


class S(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'nginx'
    sys_version = ''

    def _set_headers(self):

        self.send_response(200)

        mimetypes = {"json": "application/json", "map": "application/json", "html": "text/html", "xml": "application/xml", "js": "text/javascript", "css": "text/css", "png": "image/png"}
        if self.path.endswith((".html",".json",".css",".map",".png",".js", ".xml")):
            self.send_header('Content-type', mimetypes[self.path.split(".")[-1]])
        elif self.path.startswith("/api"):
            self.send_header('Content-type', mimetypes["json"])
        else:
            self.send_header('Content-type', mimetypes["html"])

    def _set_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Hue\"')
        self.send_header('Content-type', 'text/html')

    def _set_end_headers(self, data):
        self.send_header('Content-Length', len(data))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods',
                         'GET, OPTIONS, POST, PUT, DELETE')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url_pices = self.path.rstrip('/').split('/')
        if url_pices[1].startswith("devices"):
            self._set_headers()
            if url_pices[1] == "devices?report=true":
                self._set_end_headers(bytes(json.dumps({"clients": len(clients), "id's": clients},separators=(',', ':'),ensure_ascii=False), "utf8"))
                return
            get_parameters = parse_qs(urlparse(self.path).query)
            apiKey = (base64.urlsafe_b64decode(get_parameters["apikey"][0])).decode('utf-8')
            clients.append(apiKey[-6:])
            if apiKey not in bridges:
                bridges[apiKey] = {}
                print("register bridge: " + apiKey[-6:])
            counter = 0
            while counter < 150:
                bridges[apiKey]["lastseen"] = datetime.now()
                if "action" in bridges[apiKey]:
                    self._set_end_headers(bytes(json.dumps(bridges[apiKey]["action"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    del  bridges[apiKey]["action"]
                    clients.remove(apiKey[-6:])
                    return
                sleep(0.2)
                counter += 1
            self._set_end_headers(bytes("{renew}", "utf8"))
            clients.remove(apiKey[-6:])
        elif url_pices[1].startswith("bridge"):
            if "apikey" not in self.headers:
                self.send_error(400, 'invalid api key')
            else:
                apiKey = self.headers['apikey']
                if apiKey not in bridges:
                    self.send_error(404, 'bridge not online')
                else:
                    self._set_headers()
                    # send command to hue emulator
                    bridges[apiKey]["action"] = {"method": "GET", "address": self.path.replace('/bridge','api')}
                    #return the responce from
                    while "response" not in bridges[apiKey]:
                       sleep(0.2)
                    self._set_end_headers(bytes(json.dumps(bridges[apiKey]["response"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    del bridges[apiKey]["response"]
        elif url_pices[1].startswith("discover"):
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            ip = (base64.urlsafe_b64decode(get_parameters["data"][0])).decode('utf-8')
            output = []
            if ip in discovery:
                for bridge in range(len(discovery[ip])):
                    output.append({"id": discovery[ip][bridge]["id"],"internalipaddress": discovery[ip][bridge]["ip"]})
            self._set_end_headers(bytes(json.dumps(output,ensure_ascii=False), "utf8"))
            
            
        else:
            self.send_error(404, 'not found')
    def do_POST(self):
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        post_dictionary = json.loads(self.data_string.decode('utf8'))
        url_pices = self.path.rstrip('/').split('/')
        if url_pices[1].startswith("devices"):
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            apiKey = (base64.urlsafe_b64decode(get_parameters["apikey"][0])).decode('utf-8')
            bridges[apiKey]["response"] = post_dictionary
            self._set_end_headers(bytes("{success}", "utf8"))

        elif url_pices[1].startswith("bridge"):
            if "apikey" not in self.headers:
                self.send_error(404, 'invalid http header')
            else:
                apiKey = self.headers['apikey']
                self._set_headers()
                bridges[apiKey]["action"] = {"method": "POST", "address": self.path.replace('/bridge','api'), "body": post_dictionary}
                counter = 0
                while "response" not in bridges[apiKey] and counter < 200:
                    sleep(0.1)
                    counter+=1
                if counter == 200:
                    self._set_end_headers(bytes('{"client response timeout"}', "utf8"))
                else:
                    self._set_end_headers(bytes(json.dumps(bridges[apiKey]["response"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    del bridges[apiKey]["response"]
        elif url_pices[1].startswith("discover"):
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            ip = (base64.urlsafe_b64decode(get_parameters["data"][0])).decode('utf-8')
            self._set_end_headers(bytes('{"ok"}', "utf8"))
            if ip not in discovery:
                discovery[ip] = []
            bridgeExist = False
            for bridge in range(len(discovery[ip])):
                if post_dictionary["id"].lower() == discovery[ip][bridge]["id"]:
                    bridgeExist = True 
                    discovery[ip][bridge]["lastseen"] = datetime.now()
                    discovery[ip][bridge]["internalipaddress"] = post_dictionary["internalipaddress"]
            if bridgeExist == False:
                discovery[ip].append({"id": post_dictionary["id"].lower(), "ip": post_dictionary["internalipaddress"], "mac":  post_dictionary["macaddress"], "name": post_dictionary["name"], "lastseen": datetime.now()})

        else:
            self.send_error(404, 'not found')

    def do_PUT(self):
        if "apikey" not in self.headers:
            self.send_error(404, 'invalid http header')
        else:
            apiKey = self.headers['apikey']
            url_pices = self.path.rstrip('/').split('/')
            if url_pices[1].startswith("bridge"):
                self._set_headers()
                self.data_string = self.rfile.read(int(self.headers['Content-Length']))
                put_dictionary = json.loads(self.data_string.decode('utf8'))
                bridges[apiKey]["action"] = {"method": "PUT", "address":self.path.replace('/bridge','api'), "body": put_dictionary}
                counter = 0
                while "response" not in bridges[apiKey] and counter < 300:
                    sleep(0.05)
                    counter+=1
                if counter == 300:
                    self._set_end_headers(bytes('{"client response timeout"}'), "utf8")
                else:
                    self._set_end_headers(bytes(json.dumps(bridges[apiKey]["response"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    del bridges[apiKey]["response"]
            else:
                self.send_error(404, 'not found')

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self._set_end_headers(bytes(json.dumps([{"status": "success"}]), "utf8"))

    def do_DELETE(self):
        self._set_headers()
        url_pices = self.path.rstrip('/').split('/')

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run(https, server_class=ThreadingSimpleServer, handler_class=S):
    if https:
        server_address = ('', 443)
        httpd = server_class(server_address, handler_class)
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile="./cert.pem")
        ctx.options |= ssl.OP_NO_TLSv1
        ctx.options |= ssl.OP_NO_TLSv1_1
        ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
        ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
        ctx.set_ecdh_curve('prime256v1')
        #ctx.set_alpn_protocols(['h2', 'http/1.1'])
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        logging.info('Starting ssl httpd...')
    else:
        server_address = ('', 81)
        httpd = server_class(server_address, handler_class)
        logging.info('Starting httpd...')
    httpd.serve_forever()
    httpd.server_close()

def cleanQueue():
    while True:
        now = datetime.now()
        for apiKey in list(bridges):
            if (now - bridges[apiKey]["lastseen"]).total_seconds() > 120:
                del bridges[apiKey]
                print("remove user: " + apiKey[-6:])
        for ip in list(discovery):
            for bridge in range(len(discovery[ip])):
                if (now - discovery[ip][bridge]["lastseen"]).total_seconds() > 120:
                    del discovery[ip][bridge]
                    if len(discovery[ip]) == 0:
                        del discovery[ip]
        sleep(60)

if __name__ == "__main__":
        print("starting...")
        Thread(target=cleanQueue).start()
        run(False)
