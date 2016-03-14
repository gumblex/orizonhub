#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import kenlm
import pangu
import pickle
import struct
import random
import itertools
import functools
import collections

srandom = random.SystemRandom()

RE_UCJK = re.compile(
    '([\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff'
    '\U0001F000-\U0001F8AD\U00020000-\U0002A6D6]+)')

RE_EN = re.compile('[a-zA-Z0-9_]')

punct = frozenset(
    '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~¢£¥·ˇˉ―‖‘’“”•′‵、。々'
    '〈〉《》「」『』【】〔〕〖〗〝〞︰︱︳︴︵︶︷︸︹︺︻︼︽︾︿﹀﹁﹂﹃﹄'
    '﹏﹐﹒﹔﹕﹖﹗﹙﹚﹛﹜﹝﹞！（），．：；？［｛｜｝～､￠￡￥')

unpackvals = lambda b: struct.unpack('>' + 'H' * (len(b) // 2), b)
sel_best = lambda weights: max(enumerate(weights), key=lambda x: x[1])


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

    def __contains__(self, item):
        return item in self.cache


def weighted_choice_king(weights):
    total = 0
    winner = 0
    winweight = 0
    for i, w in enumerate(weights):
        total += w
        if srandom.random() * total < w:
            winner = i
            winweight = w
    return winner, winweight


def _get_indexword(model):
    @functools.lru_cache(maxsize=50)
    def indexword(word):
        try:
            return model.voc.index(word)
        except ValueError:
            return None
    return indexword


def joinword(words):
    last = False
    for w in words:
        if last and RE_EN.match(w[0]):
            yield ' '
        yield w
        if RE_EN.match(w[-1]):
            last = True


class SimpleModel:

    def __init__(self, lm, dictfile, ctxmodel=None, dictinit=''):
        self.lm = kenlm.LanguageModel(lm)
        self.voc = []
        self._vocid = LRUCache(64)
        self.ctx = pickle.load(open(ctxmodel, 'rb')) if ctxmodel else {}
        self.stopfn = lambda s: len(s) > 40 or len(s) > 3 and all(i == s[-1] for i in s[-3:])
        self.loaddict(dictfile, dictinit, True)

    def add_word(self, word):
        if word not in self.dic:
            self.dic.append(word)

    def loaddict(self, fn, init='', withsp=False):
        dic = set(init)
        with open(fn) as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                dic.add(ln if withsp else ln.split()[0])
        self.voc = sorted(dic)

    def indexword(self, word):
        if word not in self._vocid:
            try:
                self._vocid[word] = self.voc.index(word)
            except ValueError:
                self._vocid[word] = None
        return self._vocid[word]

    def say(self, context=(), continuewords=()):
        context = context or continuewords
        ctxvoc = list(frozenset(self.voc).intersection(map(self.voc.__getitem__, frozenset(itertools.chain.from_iterable(map(unpackvals, map(self.ctx.__getitem__, filter(None, map(self.indexword, frozenset(context)))))))))) or self.voc if context else self.voc
        out = []
        stack = list(continuewords)
        if stack:
            history = ' '.join(stack) + ' '
            idx, w = weighted_choice_king(
                10**self.lm.score(history + c, 1, 0) for c in ctxvoc)
        else:
            idx, w = weighted_choice_king(
                10**self.lm.score(c, 1, 0) for c in ctxvoc)
        out.append(ctxvoc[idx])
        stack.append(ctxvoc[idx])
        while 1:
            bos = (len(stack) <= self.lm.order + 2)
            history = ' '.join(stack[-self.lm.order - 2:]) + ' '
            idx, w = weighted_choice_king(
                10**self.lm.score(history + ctxvoc[k // 2], bos, k % 2) for k in range(len(ctxvoc) * 2))
            c = ctxvoc[idx // 2]
            out.append(c)
            stack.append(c)
            if idx % 2 or self.stopfn(out):
                break
        return pangu.spacing(''.join(joinword(out)))


class POSModel:

    allpos = (
        'a', 'ad', 'ag', 'an', 'b', 'c', 'd', 'df', 'dg', 'e', 'f', 'g', 'h', 'i',
        'j', 'k', 'l', 'm', 'mg', 'mq', 'n', 'ng', 'nr', 'ns', 'nt', 'nz', 'o',
        'p', 'q', 'r', 'rg', 'rr', 'rz', 's', 't', 'tg', 'u', 'ud', 'ug', 'uj',
        'ul', 'uv', 'uz', 'v', 'vd', 'vg', 'vi', 'vn', 'vq', 'x', 'y', 'z', 'zg',
        '“', '”', '、', '。', '！', '，', '．', '：', '；', '？'
    )

    def __init__(self, lm, poslm, dictfile):
        self.lm = kenlm.LanguageModel(lm)
        self.poslm = kenlm.LanguageModel(poslm)
        self.posvoc = {}
        self.end = frozenset('。！？”')
        self.loaddict(dictfile)

    def loaddict(self, fn):
        with open(fn) as f:
            for ln in f:
                l = ln.strip()
                if not l:
                    continue
                try:
                    w, f, p = l.split()
                    p = p[:2]
                    if RE_UCJK.match(w):
                        if p in self.posvoc:
                            self.posvoc[p].append(w)
                        else:
                            self.posvoc[p] = [w]
                except Exception:
                    pass

    def generate_pos(self):
        out = []
        idx, w = weighted_choice_king(
            10**self.poslm.score(c, 1, 0) for c in self.allpos)
        out.append(self.allpos[idx])
        yield self.allpos[idx]
        while 1:
            bos = (len(out) <= self.poslm.order + 2)
            history = ' '.join(out[-self.poslm.order - 2:]) + ' '
            idx, w = weighted_choice_king(
                10**self.poslm.score(history + self.allpos[k // 2], bos, k % 2) for k in range(len(self.allpos) * 2))
            c = self.allpos[idx // 2]
            out.append(c)
            yield c
            if idx % 2 or c in self.end:
                break

    def say(self):
        orderlm = self.lm.order
        out = []
        for pos in self.generate_pos():
            if pos in punct:
                out.append(pos)
            elif pos in self.posvoc:
                bos = (len(out) <= orderlm + 2)
                history = ' '.join(out[-orderlm - 2:]) + ' '
                availvoc = self.posvoc[pos]
                idx, w = weighted_choice_king(
                    10**self.lm.score(history + c, bos, 0) for c in availvoc)
                c = availvoc[idx]
                out.append(c)
            else:
                out.append(pos)
        return pangu.spacing(''.join(joinword(out)))


if __name__ == '__main__':
    model = SimpleModel(*sys.argv[1:])
    for ln in sys.stdin:
        ln = ln.strip()
        if ln:
            mode = ln[0]
            words = ln[1:].split()
        else:
            mode, words = '', ()
        print(model.say(words))
        sys.stdout.flush()

    #model = POSModel(*sys.argv[1:])
    #while 1:
        #print(model.say())
        #sys.stdout.flush()
