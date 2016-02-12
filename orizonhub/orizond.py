#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import logging
import operator
import threading
import functools
import collections
import concurrent.futures

import provider

__version__ = '2.0'

signames = {k: v for v, k in reversed(sorted(signal.__dict__.items()))
     if v.startswith('SIG') and not v.startswith('SIG_')}

class MsgServer():
    def __init__(self, protocals, loggers):
        self.protocals = protocals
        self.loggers = loggers
        self.cmdh = provider.CommandHandler(self)
        self.executor = concurrent.futures.ThreadPoolExecutor(20)
        self.protocal_futures = []
        self.stop = threading.Event()

    def newmsg(self, msg, cmd=True):
        fs = [self.executor.submit(h.onmsg, msg) for h in self.loggers]
        for f in fs:
            f.result(timeout=10)
        if cmd:
            return self.executor.submit(self.cmdh.onmsg, msg).result(timeout=10)

    def logmsg(self, msg):
        logging.info(msg)

    def signal(self, signum, frame):
        if signum in (signal.SIGINT, signal.SIGTERM):
            logging.info('Got signal %s: exiting...' % signames[signum])
            self.teardown()
        elif signum == signal.SIGUSR1:
            logging.info('Got signal %s: committing db...' % signames[signum])

    def setup(self):
        self.p = {}
        for p in self.loggers:
            self.p[p.name] = p
            p.setup(self)
        for p in self.protocals:
            self.p[p.name] = p
            p.setup(self)
            self.protocal_futures.append(self.executor.submit(p.run))

    def teardown(self):
        self.stop.set()
        [p.teardown() for p in self.protocals]
        [p.teardown() for p in self.loggers]
        self.executor.shutdown(False)
        [p.result(1) for p in self.protocal_futures]

    def __getattr__(self, name):
        try:
            return self.p[name]
        except KeyError:
            raise AttributeError


protocals = [
    #provider.TCPSocketProtocal('0.0.0.0', 12342),
    #provider.TelegramBotProtocal(),
    provider.DummyProtocal()
]
loggers = [
    provider.SimpleLogger()
]


loglevel = logging.DEBUG if sys.argv[-1] == '-d' else logging.INFO
logging.basicConfig(stream=sys.stdout, format='# %(asctime)s [%(levelname)s] %(message)s', level=loglevel)

MSrv = MsgServer(protocals, loggers)
MSrv.setup()
signal.signal(signal.SIGINT, MSrv.signal)
signal.signal(signal.SIGTERM, MSrv.signal)
signal.signal(signal.SIGUSR1, MSrv.signal)
logging.info("Satellite launched. Pid: %s" % os.getpid())
MSrv.stop.wait()
