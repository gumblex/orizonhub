#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import signal
import difflib
import datetime
import collections

signames = {k: v for v, k in reversed(sorted(signal.__dict__.items()))
     if v.startswith('SIG') and not v.startswith('SIG_')}

re_ntnone = re.compile(r'\w+=None(, )?')
re_usertype = re.compile(r'<(UserType.\w+): \d+>')
nt_repr = lambda nt: re_usertype.sub('\\1', re_ntnone.sub('', str(nt)))

def uniq(seq, key=None): # Dave Kirby
    # Order preserving
    seen = set()
    if key:
        return [x for x in seq if key(x) not in seen and not seen.add(key(x))]
    else:
        return [x for x in seq if x not in seen and not seen.add(x)]

def nt_from_dict(nt, d, default=None):
    kwargs = dict.fromkeys(nt._fields, default)
    kwargs.update(d)
    return nt(**kwargs)

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
        return obj
    else:
        return obj

class LRUCache(collections.UserDict):
    def __init__(self, maxlen):
        self.capacity = maxlen
        self.data = collections.OrderedDict()

    def __getitem__(self, key):
        value = self.data.pop(key)
        self.data[key] = value
        return value

    def get(self, key, default=None):
        try:
            value = self.data.pop(key)
            self.data[key] = value
            return value
        except KeyError:
            return default

    def __setitem__(self, key, value):
        try:
            self.data.pop(key)
        except KeyError:
            if len(self.data) >= self.capacity:
                self.data.popitem(last=False)
        self.data[key] = value

class LimitedSizeDict(collections.OrderedDict):
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        collections.OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        collections.OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)

def timestring_a(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return '%d:%02d:%02d' % (h, m, s)

def smartname(user, limit=20):
    if not user.protocol.startswith('telegram') and user.username:
        un = user.username
    elif user.alias:
        un = user.alias
    elif user.first_name:
        un = user.first_name
        if user.last_name:
            un += ' ' + user.last_name
    elif user.username:
        un = user.username
    else:
        un = '<%s>' % 'Unknown'[:limit-2]
    while len(un) > limit:
        unl = un.rsplit(' ', 1)
        if len(unl) > 1:
            un = unl[0]
        else:
            un = un[:limit]
    else:
        return un.rstrip(' -|[]')

def fwd_to_text(messages, timezone, withid=False, withuser=True):
    lines = []
    for m in messages:
        # [%d|%s] %s: %s
        lines.append('[%s%s] %s%s' % (
            str(messages.id) + '|' if withid and messages.id else '',
            datetime.datetime.fromtimestamp(m.time, timezone).strftime(
            '%Y-%m-%d %H:%M'),
            smartname(m.src) + ': ' if withuser else '',
            m.text
        ))
    if lines:
        return '\n'.join(lines)
    else:
        return 'Message%s not found.' % ('s' if len(messages) > 1 else '')

def sededit(a, b):
    start1, end1, start2, end2 = None, None, None, None
    s = difflib.SequenceMatcher(None, a, b)
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'equal':
            continue
        if start1:
            end1, end2 = i2, j2
        else:
            start1, start2 = i1, j1
    return 's/%s/%s/' % (a[start1:end1], b[start2:end2])
