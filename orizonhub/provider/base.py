#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
import threading
import functools

import urllib.request

__version__ = '2.0'

class LRUCache:

    def __init__(self, maxlen):
        self.capacity = maxlen
        self.cache = collections.OrderedDict()

    def __getitem__(self, key):
        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def get(self, key, default=None):
        try:
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        except KeyError:
            return default

    def __setitem__(self, key, value):
        try:
            self.cache.pop(key)
        except KeyError:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
        self.cache[key] = value

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

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

def Message(msg={}, protocal='raw', text='', **kwargs):
    d = {'protocal': protocal, 'text': text, 'time': int(time.time())}
    d.update(msg)
    d.update(kwargs)
    return AttrDict(d)

class Provider:
    def setup(self, host):
        self.host = host

    def teardown(self):
        pass

class MessageProtocal(Provider):
    pass

class MessageLogger(Provider):
    def onmsg(self, msg):
        raise NotImplementedError

class DummyProtocal(MessageProtocal):
    name = 'dummy'

    def run(self):
        while not self.host.stop.is_set():
            #self.host.newmsg(Message(protocal=self.name, text='Test.'))
            print(self.host.newmsg(Message(protocal=self.name, text='/233')))
            t = urllib.request.urlopen('http://127.0.0.1:7657/').read().decode()
            print(self.host.newmsg(Message(protocal=self.name, text=t)))
