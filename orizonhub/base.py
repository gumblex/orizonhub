#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import enum
import logging
import threading
import functools
import collections
import concurrent.futures

import pytz

from . import utils
from .config import config

__version__ = '2.0'

config = utils.wrap_attrdict(config)

logger = logging.getLogger('orizond')
logger.setLevel(logging.DEBUG if config.debug else logging.INFO)

timezone = pytz.timezone(config.timezone)
executor = concurrent.futures.ThreadPoolExecutor(20)

# Global provider registry
commands = collections.OrderedDict()
protocols = {}
loggers = {}
forwarders = {}

def register_protocols(d):
    for k, v in d.items():
        pass

Command = collections.namedtuple('Command', ('func', 'usage', 'protocol'))

def register_command(name, usage=None, protocol=None, enabled=True):
    def wrapper(func):
        if enabled:
            commands[name] = Command(func, usage or func.__doc__, protocol)
        return func
    return wrapper




class Protocol:
    pass





def async_method(func):
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        return self.host.executor.submit(self.func, *args, **kwargs)
    return wrapped

def noerr_func(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            logging.exception('Async function failed.')
    return wrapped

