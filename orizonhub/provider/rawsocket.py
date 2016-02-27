#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import io
import json
import socketserver
from multiprocessing.connection import Connection

from ..utils import nt_from_dict
from ..model import Message, Response, Protocol

class RawSocketProtocol(Protocol):
    '''
    Request:
    {"type": "message", "async": true, "message": {<Message>}}
    ==> true
    {"type": "message", "async": false, "message": {<Message>}}
    ==> {"type": "response", "response": <Response>}
    '''

    def __init__(self, config, bus):
        self.config = config
        self.bus = bus
        self.handlers = []
        if type(config.address) == tuple:
            self.sockserv = socketserver.TCPServer(config.address, _request_handler(self.handlers, bus))
        elif type(config.address) is str:
            self.sockserv = socketserver.UnixStreamServer(config.address, _request_handler(self.handlers, bus))

    def start_polling(self):
        self.sockserv.serve_forever()

    def send(self, response):
        for h in self.handlers:
            h.send(response)

    def forward(self, msg, protocol):
        for h in self.handlers:
            h.send(msg)

    def exit(self):
        self.sockserv.shutdown()
        try:
            os.unlink(self.config.address)
        except Exception:
            pass

def _request_handler(registry, bus):
    class RawSocketHandler(socketserver.BaseRequestHandler):
        def setup(self):
            registry.append(self)

        def handle(self):
            self.conn = Connection(self.request.detach())
            while self.conn._handle:
                try:
                    obj = json.loads(self.conn.recv_bytes().decode('utf-8'))
                except EOFError:
                    break
                if obj.get('async', True):
                    bus.post(nt_from_dict(Message, obj['message'], None))
                    self.conn.send_bytes(json.dumps(True).encode('utf-8'))
                else:
                    m = bus.post_sync(nt_from_dict(Message, obj['message'], None))
                    ret = {"type": "response", "response": m._asdict() if m else None}
                    self.conn.send_bytes(json.dumps(ret).encode('utf-8'))

        def send(self, msg):
            if isinstance(msg, Message):
                ret = {"type": "message", "message": msg._asdict()}
            else:
                ret = {"type": "response", "response": msg._asdict()}
            self.conn.send_bytes(json.dumps(ret).encode('utf-8'))

        def finish(self):
            registry.remove(self)

    return RawSocketHandler
