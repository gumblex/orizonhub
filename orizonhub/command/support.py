#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import logging
import resource
import threading
import subprocess
import collections
import concurrent.futures

from ..model import Message, Command, Response

logger = logging.getLogger('cmd')

class CommandProvider:
    def __init__(self):
        self.bus = None
        self.config = None
        self.external = ExternalCommandProvider()
        self.general_handlers = collections.OrderedDict()
        self.commands = collections.OrderedDict()

    def activate(self, bus, config):
        self.bus = bus
        self.config = config
        self.external.start()

    def register_handler(self, name, protocol=None, mtype=None, dependency=None, enabled=True):
        def wrapper(func):
            if enabled:
                self.general_handlers[name] = Command(func, func.__doc__, protocol, mtype, dependency)
            return func
        return wrapper

    def register_command(self, name, protocol=None, mtype=None, dependency=None, enabled=True):
        def wrapper(func):
            if enabled:
                self.commands[name] = Command(func, func.__doc__, protocol, mtype, dependency)
            return func
        return wrapper

    def close(self):
        self.external.close()

    def __getattr__(self, name):
        try:
            return self.commands[name]
        except KeyError:
            raise AttributeError("command %r not found" % name)

class ExternalCommand:
    def __init__(self, buffered=False, once=False):
        ...

    def __call__(self):
        raise NotImplementedError

    def communicate(self, input=None):
        ...

    def setsplimits(self, cputime, memory):
        def _setlimits():
            resource.setrlimit(resource.RLIMIT_CPU, cputime)
            resource.setrlimit(resource.RLIMIT_RSS, memory)
            resource.setrlimit(resource.RLIMIT_NPROC, (1024, 1024))
        return _setlimits

class ExternalCommandProvider:
    '''
    This class implements the old way of running resource-intensive commands
    in a subprocess, where the command behavior can be safely managed.
    '''
    DIR = os.path.dirname(__file__)
    CMD = ('python3', os.path.join(DIR, 'extapp.py'))

    def __init__(self):
        self.proc = None
        self.lock = threading.Lock()
        self.task = {}
        self.run = False
        self.thread = None

    def start(self):
        self.run = True
        self.checkappproc()
        self.thread = threading.Thread(target=self.getappresult, name=repr(self))
        self.thread.daemon = True
        self.thread.start()

    def checkappproc(self):
        if self.run and self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(self.CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=self.DIR)

    def __call__(self, cmd, *args):
        with self.lock:
            # Prevent float problems
            tid = str(time.perf_counter())
            text = json.dumps({"cmd": cmd, "args": args, "id": tid})
            fut = self.task[tid] = concurrent.futures.Future()
            try:
                self.proc.stdin.write(text.strip().encode('utf-8') + b'\n')
                self.proc.stdin.flush()
            except BrokenPipeError:
                self.checkappproc()
                self.proc.stdin.write(text.strip().encode('utf-8') + b'\n')
                self.proc.stdin.flush()
            logger.debug('Wrote to extapp: ' + text)
            return fut

    def getappresult(self):
        while self.run:
            try:
                result = self.proc.stdout.readline().strip().decode('utf-8')
            except BrokenPipeError:
                self.checkappproc()
                result = self.proc.stdout.readline().strip().decode('utf-8')
            if result:
                logging.debug('Got from extapp: ' + result)
                obj = json.loads(result)
                fut = self.task.get(obj['id'])
                if fut:
                    if obj['exc']:
                        fut.set_exception(Exception(obj['exc']))
                        logging.error('Remote app server error.\n' + obj['exc'])
                    else:
                        fut.set_result(obj['ret']) # or 'Empty.'
                    del self.task[obj['id']]
                else:
                    logging.error('Task not found, result: %r' % obj)

    def restart(self):
        self.proc.terminate()
        self.proc = subprocess.Popen(self.CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.checkappproc()
        logging.info('External command provider restarted.')

    def close(self):
        self.run = False
        if self.proc:
            self.proc.terminate()

cp = CommandProvider()
