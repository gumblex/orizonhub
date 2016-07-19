#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import io
import json
import collections
import socketserver
from multiprocessing.connection import Connection

from .utils import nt_from_dict
from .model import Message, Response, Protocol

class RawSocketProtocol(Protocol):
    '''
    > {"type": "message", "message": {<Message>}}
    < {"ret": true}
    > {"type": "request", "request": {<Request>}}
    < {"ret": true, "response": {<Response>}}
    < {"ret": false, "response": null}
    > {"type": "get_updates", "offset": <int>}
    < {"ret": true, "offset": <int>, "messages": [{<Message>}]}
    '''

    def __init__(self, config, bus):
        self.config = config
        self.bus = bus
        self.pastebin = bus.pastebin
        self.handlers = []
        self.sockhdl = _request_handler(self.handlers, bus)
        address = config.protocols.socket.address
        if type(address) == tuple:
            self.sockserv = socketserver.TCPServer(address, self.sockhdl)
        elif type(address) is str:
            self.sockserv = socketserver.UnixStreamServer(address, self.sockhdl)

    def start_polling(self):
        self.sockserv.serve_forever()

    def send(self, response, protocol, forwarded):
        for h in self.handlers:
            h.send(response)

    def forward(self, msg, protocol):
        for handler in self.protocols[protocol]:
            handler.send(msg, protocol)

    def close(self):
        try:
            for h in self.handlers:
                h.close()
            self.sockserv.shutdown()
        finally:
            try:
                os.unlink(self.config.protocols.socket.address)
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
                if obj['type'] == 'message':
                    bus.post(nt_from_dict(Message, obj['message'], None))
                    self.conn.send_bytes(json.dumps({'ret': True}).encode('utf-8'))
                elif obj['type'] == 'request':
                    m = bus.post_sync(nt_from_dict(Message, obj['message'], None))
                    if m:
                        ret = {"ret": True, "response": m._asdict()}
                    else:
                        ret = {"ret": False, "response": None}
                    self.conn.send_bytes(json.dumps(ret).encode('utf-8'))

        def send(self, msg):
            if isinstance(msg, Message):
                ret = {"type": "message", "message": msg._asdict()}
            else:
                ret = {"type": "response", "response": msg._asdict()}
            self.conn.send_bytes(json.dumps(ret).encode('utf-8'))

        def finish(self):
            registry.remove(self)

        def close(self):
            self.conn.close()

    return RawSocketHandler
