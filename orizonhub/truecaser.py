#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import collections

re_eng = re.compile('([A-Za-z]+)')

def dumpdict(d, fp):
    for k in sorted(d):
        fp.write(('%s\t%s\n' % (k, d[k])).encode('utf-8'))

def loaddict(fp):
    d = {}
    for ln in fp:
        ln = ln.strip().decode('utf-8').split('\t')
        if len(ln) == 2:
            d[ln[0]] = ln[1]
    return d

def train(iterable):
    d = collections.defaultdict(collections.Counter)
    for ln in iterable:
        for tok in re_eng.split(ln):
            if 1 < len(tok) < 25 and re_eng.match(tok):
                d[tok.lower()][tok] += 1
    for word, val in tuple(d.items()):
        if sum(val.values()) > 1:
            d[word] = val.most_common(1)[0][0]
        else:
            del d[word]
    return dict(d)

class Truecaser:
    def __init__(self, wmap):
        self.wmap = wmap

    def truecase(self, text):
        res = []
        for tok in re_eng.split(text):
            res.append(self.wmap.get(tok.lower(), tok))
        return ''.join(res)

if __name__ == '__main__':
    filename = sys.argv[-1]

    if len(sys.argv) > 2:
        d = train(sys.stdin)
        dumpdict(d, open(filename, 'wb'))
    else:
        tc = Truecaser(loaddict(open(filename, 'rb')))
        for ln in sys.stdin:
            sys.stdout.write(tc.truecase(ln))
