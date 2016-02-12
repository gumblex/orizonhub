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
        


Command = collections.namedtuple('Command', ('func', 'usage', 'scope'))

def register_command(name, usage=None, protocol=None, enabled=True):
    def wrapper(func):
        if enabled:
            commands[name] = Command(func, usage or func.__doc__, protocol)
        return func
    return wrapper

def _requires_unix_version(sysname, min_version):
    """Decorator raising SkipTest if the OS is `sysname` and the version is less
    than `min_version`.

    For example, @_requires_unix_version('FreeBSD', (7, 2)) raises SkipTest if
    the FreeBSD version is less than 7.2.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            if platform.system() == sysname:
                version_txt = platform.release().split('-', 1)[0]
                try:
                    version = tuple(map(int, version_txt.split('.')))
                except ValueError:
                    pass
                else:
                    if version < min_version:
                        min_version_txt = '.'.join(map(str, min_version))
                        raise unittest.SkipTest(
                            "%s version %s or higher required, not %s"
                            % (sysname, min_version_txt, version_txt))
            return func(*args, **kw)
        wrapper.min_version = min_version
        return wrapper
    return decorator




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

