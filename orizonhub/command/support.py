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
        self.general_handlers = collections.OrderedDict()
        self.commands = collections.OrderedDict()

    def activate(self, bus, config):
        self.bus = bus
        self.config = config

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
        pass

    def __getattr__(self, name):
        try:
            return self.commands[name]
        except KeyError:
            raise AttributeError("command %r not found" % name)

cp = CommandProvider()
