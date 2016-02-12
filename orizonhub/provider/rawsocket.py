#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .base import *

class TCPSocketProtocal(MessageProtocal):
    def __init__(self, tcphost, tcpport):
        self.tcphost = tcphost
        self.tcpport = tcpport

    def setup(self, host):
        self.host = host
        self.sock = yield from asyncio.start_server(self.onrecv, self.tcphost, self.tcpport, loop=self.host.loop)
        logging.info('Socket established')

    def onrecv(self, reader, writer):
        while 1:
            data = yield from reader.readline()
            if not data:
                break
            message = data.decode('utf-8')
            addr = writer.get_extra_info('peername')
            logging.info("Received %r from %r" % (message, addr))
            yield from self.host.newmsg(Message('raw', message))
