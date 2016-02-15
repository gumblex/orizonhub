#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import signal
import collections

signames = {k: v for v, k in reversed(sorted(signal.__dict__.items()))
     if v.startswith('SIG') and not v.startswith('SIG_')}

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

def wrap_attrdict(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = wrap_attrdict(v)
        return AttrDict(obj)
    elif isinstance(obj, list):
        for k, v in enumerate(obj):
            obj[k] = wrap_attrdict(v)
    else:
        return obj

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
