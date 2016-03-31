#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import itertools
from math import log
from .pinyinlookup import logtotal, p_prob, p_abbr

import dawg

p_index = {}
essay = {}

_ig1 = lambda x: x[1]

def loaddict(f_index='pyindex.dawg', f_essay='essay.dawg'):
    global essay, p_index
    p_index = dawg.BytesDAWG()
    p_index.load(f_index)
    essay = dawg.IntDAWG()
    essay.load(f_essay)

essayget = lambda w: -essay.get(w, 0) / 1000000 or -logtotal

def pinyininput(sentence):
    DAG = {}
    edges = {}
    N = len(sentence)
    for k in range(N):
        tmplist = []
        i = k
        frag = sentence[k]
        while i < N and frag in p_index:
            words = p_index[frag]
            if words[0]:
                tmplist.append(i)
                edges[(k, i)] = max(((w, essayget(w) + p_prob.get((w.decode('utf-8'), frag), 0)) for w in words), key=_ig1)
            i += 1
            frag = sentence[k:i + 1]
        if not tmplist:
            tmplist.append(k)
            abbr = p_abbr.get(sentence[k])
            if abbr:
                edges[(k, k)] = max(((w, essayget(w) + p_prob.get((w.decode('utf-8'), frag), 0)) for w, frag in itertools.chain.from_iterable(((wrd, c) for wrd in p_index[c]) for c in abbr)), key=_ig1)
        DAG[k] = tmplist

    route = {N: (0, 0)}
    for idx in range(N - 1, -1, -1):
        route[idx] = max((edges.get((idx,x), (None, -50))[1] + route[x + 1][0], x) for x in DAG[idx])

    result = []
    x = 0
    while x < N:
        y = route[x][1]
        result.append(edges.get((x, y), (sentence[x:y+1].encode('utf-8'), -50))[0])
        x = y + 1

    return b''.join(result).decode('utf-8')

if __name__ == '__main__':
    loaddict()
    while 1:
        print(pinyininput(input('> ')))
