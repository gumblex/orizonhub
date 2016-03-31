#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pickle
import random
import bisect
import operator
import functools
import itertools
from math import log
from .common_surnames import d as common_surnames
from .lookuptable import chrevlookup, pinyintrie, surnamerev

for py in tuple(chrevlookup.keys()):
    for ch in range(len(py)):
        frag = py[:ch+1]
        if frag not in chrevlookup:
            chrevlookup[frag] = ''

logtotal = log(sum(len(s) for s in chrevlookup.values()))

ig1 = operator.itemgetter(1)

phonetic_symbol = {
"ā": "a",
"á": "a",
"ǎ": "a",
"à": "a",
"ē": "e",
"é": "e",
"ě": "e",
"è": "e",
"ō": "o",
"ó": "o",
"ǒ": "o",
"ò": "o",
"ī": "i",
"í": "i",
"ǐ": "i",
"ì": "i",
"ū": "u",
"ú": "u",
"ǔ": "u",
"ù": "u",
"ü": "v",
"ǖ": "v",
"ǘ": "v",
"ǚ": "v",
"ǜ": "v",
"ń": "n",
"ň": "n",
"": "m"
}


def untone(text):
    # This is a limited version only for entities defined in xml_escape_table
    for k, v in phonetic_symbol.items():
        text = text.replace(k, v)
    return text


class WeightedRandomGenerator(object):

    def __init__(self, weights):
        self.totals = list(itertools.accumulate(weights))
        self.total = self.totals[-1]

    def __iter__(self):
        return self

    def __next__(self):
        rnd = random.random() * self.total
        return bisect.bisect_right(self.totals, rnd)

    def __call__(self):
        return self.__next__()


def _pyword_tokenize(word):
    DAG = {}
    N = len(word)
    for k in range(N):
        tmplist = []
        i = k
        frag = word[k]
        while i < N and frag in chrevlookup:
            if chrevlookup[frag]:
                tmplist.append(i)
            i += 1
            frag = word[k:i + 1]
        if not tmplist:
            tmplist.append(k)
        DAG[k] = tmplist
    route = {N: (0, 0)}
    for idx in range(N - 1, -1, -1):
        route[idx] = max((log(len(chrevlookup.get(word[idx:x + 1], '')) or 1) -
                          logtotal + route[x + 1][0], x) for x in DAG[idx])
    result = []
    x = 0
    while x < N:
        y = route[x][1] + 1
        result.append(word[x:y])
        x = y
    return result

pytokenize = lambda s: list(itertools.chain.from_iterable(_pyword_tokenize(w) for w in s.replace("'", ' ').lower().split()))

surnamesortkey = lambda n: -common_surnames.get(n, 0.00001)

class NameModel(object):

    def __init__(self, modelname):
        with open(modelname, 'rb') as f:
            self.firstchar, self.secondchar = pickle.load(f)

        del self.secondchar['']
        self.snlst, snprb = tuple(zip(*common_surnames.items()))
        self.fclst, fcprb = tuple(zip(*self.firstchar.items()))
        self.sclst, scprb = tuple(zip(*self.secondchar.items()))
        self.sngen = WeightedRandomGenerator(snprb)
        self.fcgen = WeightedRandomGenerator(fcprb)
        self.scgen = WeightedRandomGenerator(scprb)

    initlookup = functools.lru_cache(maxsize=10)(lambda self, ch: ''.join(set(''.join(chrevlookup[p] for p in pinyintrie.get(ch)))) if ch in pinyintrie else ch)

    lookupsurname = lambda self, pychars: ((list(itertools.chain.from_iterable(surnamerev.get(p, ()) for p in pinyintrie[pychars[0]])) if pychars[0] in pinyintrie else [pychars[0]]) if len(pychars) == 1 and len(pychars[0]) == 1 else surnamerev.get(' '.join(pychars), []))

    lookupchar = lambda self, ch: (self.initlookup(ch) if len(ch) == 1 else (chrevlookup.get(ch) or self.initlookup(ch[0])))

    fullnamesortkey = lambda self, n: -common_surnames.get(n[0], 0.00001)*self.firstchar.get(n[1])*self.secondchar.get(n[2:])
    namesortkey = lambda self, n: -self.firstchar.get(n[0])*self.secondchar.get(n[1:])

    def splitname(self, romanization):
        words = romanization.split()
        tok = name = pytokenize(romanization)
        if not name:
            return [], []
        if len(words) == 1:
            words = name
        surnames = self.lookupsurname(pytokenize(words[0]))
        name = pytokenize(' '.join(words[1:]))
        if not surnames:
            surnames = self.lookupsurname(pytokenize(words[-1]))
            name = pytokenize(' '.join(words[:-1]))
            if len(words) > 2 and not surnames:
                surnames = self.lookupsurname(pytokenize(' '.join(words[:2])))
                name = pytokenize(' '.join(words[2:]))
        if surnames:
            surnames = sorted(frozenset(surnames), key=surnamesortkey)
        else:
            name = tok
        return surnames, name

    def selectname(self, name, num=10):
        if not name:
            return []
        evalnum = int(num ** (1/len(name))) + 1
        namechars = [sorted(filter(ig1, ((n, self.firstchar.get(n, 1e-10 if 0x4E00 <= ord(n) < 0x9FCD else 0)) for n in self.lookupchar(name[0]))), key=ig1, reverse=1)]
        namechars.extend(sorted(filter(ig1, ((n, self.secondchar.get(n, 1e-10 if 0x4E00 <= ord(n) < 0x9FCD else 0)) for n in self.lookupchar(l))), key=ig1, reverse=1)[:evalnum] for l in name[1:])
        namechars = list(filter(None, namechars))[:10]
        if not namechars:
            return []
        candidates = []
        for group in itertools.product(*namechars):
            gz = tuple(zip(*group))
            gname = ''.join(gz[0])
            gfreq = functools.reduce(operator.mul, gz[1])
            candidates.append((gname, gfreq))
        candidates.sort(key=ig1, reverse=1)
        return [x[0] for x in candidates][:num]

    def processinput(self, userinput, num=10):
        if not userinput:
            return [], [self.snlst[self.sngen()] + self.fclst[self.fcgen()] + self.sclst[self.scgen()] for i in range(num)]
        try:
            surnames, names = self.splitname(untone(userinput).lower())
            names = self.selectname(names, num=num)
            if not names:
                names = [self.fclst[self.fcgen()] + self.sclst[self.scgen()] for i in range(num)]
            return surnames, names
        except Exception:
            raise
            return [], []

    def getname(self):
        return self.snlst[self.sngen()] + self.fclst[self.fcgen()] + self.sclst[self.scgen()]

    __call__ = getname

if __name__ == '__main__':
    while 1:
        nm = NameModel('namemodel.m')
        fullname = nm.getname()
        #if name not in names:
            #print(fullname)
        print(fullname)
