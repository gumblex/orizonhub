#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import resource
import subprocess
import collections

from ..model import Command, Response

logger = logging.getLogger('cmd')

class CommandProvider:
    def __init__(self):
        self.bus = None
        self.config = None
        self.general_handlers = collections.OrderedDict()
        self.commands = collections.OrderedDict()

    def activate(self, bus, config):
        self.bus = bus
        self.config = config

    def register_handler(self, name, protocol=None, dependency=None, enabled=True):
        def wrapper(func):
            if enabled:
                self.general_handlers[name] = Command(func, func.__doc__, protocol, dependency)
            return func
        return wrapper

    def register_command(self, name, protocol=None, dependency=None, enabled=True):
        def wrapper(func):
            if enabled:
                self.commands[name] = Command(func, func.__doc__, protocol, dependency)
            return func
        return wrapper

    def __getattr__(self, name):
        try:
            return self.commands[name]
        except KeyError:
            raise AttributeError("command %r not found" % name)

class ExternalCommand:
    def __init__(self, buffered=False, once=False):
        ...

    def communicate(self, input=None):
        ...

    def setsplimits(self, cputime, memory):
        def _setlimits():
            resource.setrlimit(resource.RLIMIT_CPU, cputime)
            resource.setrlimit(resource.RLIMIT_RSS, memory)
            resource.setrlimit(resource.RLIMIT_NPROC, (1024, 1024))
        return _setlimits

cp = CommandProvider()
