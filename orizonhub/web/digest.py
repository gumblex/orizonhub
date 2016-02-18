#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import math
import json
import shutil
import sqlite3
import operator
import itertools
import collections

import jinja2
import truecaser

#import jieba
from vendor import mosesproxy as jieba
from vendor import zhconv

NAME = '##Orz'
TITLE = '##Orz 分部喵'
TIMEZONE = 8 * 3600
CUTWINDOW = (0 * 3600, 6 * 3600)
LINKWINDOW = 120
CHUNKINTERV = 120

CFG = json.load(open('config.json'))
db = sqlite3.connect('chatlog.db')
conn = db.cursor()

USER_CACHE = {}

re_word = re.compile(r"\w+", re.UNICODE)
re_tag = re.compile(r"#\w+", re.UNICODE)
re_at = re.compile('@[A-Za-z][A-Za-z0-9_]{4,31}')
re_url = re.compile(r"(^|[\s.:;?\-\]<\(])(https?://[-\w;/?:@&=+$\|\_.!~*\|'()\[\]%#,]+[\w/#](\(\))?)(?=$|[\s',\|\(\).:;?\-\[\]>\)])")
re_ircaction = re.compile('^\x01ACTION (.*)\x01$')
_ig1 = operator.itemgetter(1)

MEDIA_TYPES = {
'text': '文本',
'audio': '声音',
'document': '文件',
'photo': '图片',
'sticker': '贴纸',
'video': '视频',
'voice': '语音',
'contact': '名片',
'location': '位置',
'service': '服务'
}

SERVICE = frozenset(('new_chat_participant', 'left_chat_participant', 'new_chat_title', 'new_chat_photo', 'delete_chat_photo', 'group_chat_created'))

def daystart(sec=None):
    if not sec:
        sec = time.time()
    return int((sec + TIMEZONE) // 86400 * 86400 - TIMEZONE)

def uniq(seq, key=None): # Dave Kirby
    # Order preserving
    seen = set()
    if key:
        return [x for x in seq if key(x) not in seen and not seen.add(key(x))]
    else:
        return [x for x in seq if x not in seen and not seen.add(x)]

def db_getuser(uid):
    r = USER_CACHE.get(uid)
    if r is None:
        r = conn.execute('SELECT username, first_name, last_name FROM users WHERE id = ?', (uid,)).fetchone() or (None, None, None)
        USER_CACHE[uid] = r
    return r

def db_isbot(uid):
    return (db_getuser(uid)[0] or '').lower().endswith('bot')

def db_getufname(uid, mmedia=None):
    if uid == CFG['ircbotid']:
        if mmedia and '_ircuser' in mmedia:
            return mmedia['_ircuser']
        else:
            return '<IRC 用户>'
    else:
        name, last = db_getuser(uid)[1:]
        if last:
            name += ' ' + last
        return name or '<未知>'

def db_getfirstname(uid, mmedia=None):
    if uid == CFG['ircbotid']:
        if mmedia and '_ircuser' in mmedia:
            return mmedia['_ircuser']
        else:
            return '<IRC 用户>'
    else:
        fn = db_getufname(uid)
        return fn.split()[0]

def strftime(fmt, t=None):
    if t is None:
        t = time.time()
    t += TIMEZONE
    return time.strftime(fmt, time.gmtime(t))

def getwday(t=None):
    if t is None:
        t = time.time()
    t += TIMEZONE
    return ('周一','周二','周三','周四','周五','周六','周日')[time.gmtime(t)[6]]

def stripreaction(text):
    act = re_ircaction.match(text)
    if act:
        return act.group(1)
    else:
        return text

class DirectWeightedGraph:
    d = 0.85

    def __init__(self):
        self.graph = collections.defaultdict(list)

    def add_edge(self, start, end, weight):
        self.graph[start].append((end, weight))

    def rank(self):
        ws = collections.defaultdict(float)
        outSum = collections.defaultdict(float)

        wsdef = 1.0 / (len(self.graph) or 1.0)
        for n, out in self.graph.items():
            ws[n] = wsdef
            outSum[n] = sum((e[1] for e in out), 0.0)

        # this line for build stable iteration
        sorted_keys = sorted(self.graph.keys())
        for x in range(10):  # 10 iters
            for n in sorted_keys:
                s = 0
                for e in self.graph[n]:
                    if outSum[e[0]] and ws[e[0]]:
                        s += e[1] / outSum[e[0]] * ws[e[0]]
                ws[n] = (1 - self.d) + self.d * s

        (min_rank, max_rank) = (sys.float_info[0], sys.float_info[3])

        for w in ws.values():
            if w < min_rank:
                min_rank = w
            elif w > max_rank:
                max_rank = w

        for n, w in ws.items():
            # to unify the weights, don't *100.
            ws[n] = (w - min_rank / 10.0) / (max_rank - min_rank / 10.0)

        return ws


class DigestComposer:

    def __init__(self, date):
        self.template = 'digest.html'
        self.date = date
        self.title = ''
        self.tc = truecaser.Truecaser(truecaser.loaddict(open('vendor/truecase.txt', 'rb')))
        self.stopwords = frozenset(map(str.strip, open('vendor/stopwords.txt', 'r', encoding='utf-8')))
        self.ircbots = re.compile(r'(titlbot|varia|Akarin).*')
        self.fetchmsg(date)
        self.msgindex()

    def fetchmsg(self, date):
        '''
        Fetch messages that best fits in a day.
        '''
        start = (daystart(date) + CUTWINDOW[0], daystart(date) + CUTWINDOW[1])
        end = (daystart(date) + 86400 +
               CUTWINDOW[0], daystart(date) + 86400 + CUTWINDOW[1])
        last, lastid = start[0], 0
        msgs = collections.OrderedDict()
        intervals = ([], [])
        for mid, src, text, date, fwd_src, fwd_date, reply_id, media in conn.execute('SELECT id, src, text, date, fwd_src, fwd_date, reply_id, media FROM messages WHERE date >= ? AND date < ? ORDER BY date ASC, id ASC', (start[0], end[1])):
            msgs[mid] = (src, text or '', date, fwd_src, fwd_date, reply_id, media)
            if start[0] <= date < start[1]:
                intervals[0].append((date - last, mid))
            elif last < start[1] <= date:
                intervals[0].append((date - last, mid))
            elif end[0] <= date < end[1]:
                if last < end[0]:
                    last = end[0]
                intervals[1].append((date - last, lastid))
            last = date
            lastid = mid
        intervals[1].append((end[1] - last, lastid))
        if not msgs:
            raise ValueError('Not enough messages in (%s, %s)' % (start[0], end[1]))
        self.start = startd = msgs[max(intervals[0] or ((0, tuple(msgs.keys())[0]),))[1]][2]
        self.end = endd = msgs[max(intervals[1] or ((0, tuple(msgs.keys())[-1]),))[1]][2]
        self.msgs = collections.OrderedDict(
            filter(lambda x: startd <= x[1][2] <= endd, msgs.items()))

    def msgpreprocess(self, text):
        at = False
        for t in jieba.cut(text, HMM=False):
            if t == '@':
                at = True
            elif at:
                yield '@' + t
                at = False
            elif t.lower() not in self.stopwords:
                # t.isidentifier() and 
                yield t

    def msgindex(self):
        self.fwd_lookup = {}
        self.words = collections.Counter()
        self.msgtok = {}
        for mid, value in self.msgs.items():
            src, text, date, fwd_src, fwd_date, reply_id, media = value
            self.fwd_lookup[(src, date)] = mid
            tok = self.msgtok[mid] = tuple(self.msgpreprocess(zhconv.convert(self.tc.truecase(re_url.sub('', stripreaction(text))), 'zh-hans')))
            for w in frozenset(t.lower() for t in tok):
                self.words[w] += 1
        self.words = dict(self.words)

    def chunker(self):
        results = []
        chunk = []
        last = 0
        for mid, value in self.msgs.items():
            src, text, date, fwd_src, fwd_date, reply_id, media = value
            if date - last > CHUNKINTERV and chunk:
                results.append(chunk)
                chunk = []
            last = date
            chunk.append(mid)
        if chunk:
            results.append(chunk)
        return sorted(results, key=len, reverse=True)

    def tfidf(self, term, text):
        return text.count(term) / len(text) * math.log(len(self.msgs) / self.words.get(term, 1))

    def tfidf_kwd(self, toks, topK=15):
        toks = tuple(filter(lambda x: len(x) > 1, toks))
        toklen = len(toks)
        msglen = len(self.msgs)
        return tuple(map(_ig1, sorted((-count / toklen * math.log(msglen / self.words.get(term, 1)), term) for term, count in collections.Counter(toks).items())))[:topK]

    def tr_kwd(self, toks, topK=15):
        return jieba.analyse.textrank(' '.join(toks), topK, False, ('n', 'ns', 'nr', 'vn', 'v', 'eng'))

    def cosinesimilarity(self, a, b):
        msga = self.msgtok[a]
        msgb = self.msgtok[b]
        vcta = {w:self.tfidf(w.lower(), msga) for w in frozenset(msga)}
        vctb = {w:self.tfidf(w.lower(), msgb) for w in frozenset(msgb)}
        keys = vcta.keys() & vctb.keys()
        ma = sum(i**2 for i in vcta.values())**.5
        mb = sum(i**2 for i in vctb.values())**.5
        return (sum(vcta[i]*vctb[i] for i in keys) /
                ma / mb) if (ma and mb) else 0

    def classify(self, mid):
        '''
        0 - Normal messages sent by users
        1 - Interesting messages sent by the bots
        2 - Boring messages sent by users
        3 - Boring messages sent by the bots
        '''
        src, text, date, fwd_src, fwd_date, reply_id, media = self.msgs[mid]
        if src == CFG['botid']:
            repl = self.msgs.get(reply_id)
            if repl and (repl[1].startswith('/say') or repl[1].startswith('/reply')):
                return 1
            else:
                return 3
        elif src == CFG['ircbotid']:
            mmedia = json.loads(media or '{}')
            if self.ircbots.match(mmedia.get('_ircuser', '')):
                return 3
            else:
                return 0
        elif db_isbot(fwd_src) and len(text or '') > 75:
            return 3
        elif not text or text.startswith('/'):
            return 2
        else:
            return 0

    def hotrank(self, chunk):
        graph = DirectWeightedGraph()
        edges = {}
        similarity = self.cosinesimilarity
        for mid in chunk:
            src, text, date, fwd_src, fwd_date, reply_id, media = self.msgs[mid]
            if self.classify(mid) > 1:
                continue
            backlink = self.fwd_lookup.get((fwd_src, fwd_date)) or reply_id
            if (backlink in self.msgs and (mid, backlink) not in edges):
                edges[(mid, backlink)] = similarity(mid, backlink)
            for mid2, value2 in self.msgs.items():
                if 0 < date - value2[2] < LINKWINDOW:
                    w = edges.get((mid, mid2)) or edges.get((mid2, mid)) or similarity(mid, mid2)
                    edges[(mid, mid2)] = w
                    edges[(mid2, mid)] = w
        for key, weight in edges.items():
            if weight:
                graph.add_edge(key[0], key[1], weight)
        del edges
        return sorted(graph.rank().items(), key=_ig1, reverse=True)

    def hotchunk(self):
        for chunk in self.chunker()[:5]:
            kwds = self.tfidf_kwd(itertools.chain.from_iterable(self.msgtok[mid] for mid in chunk if self.classify(mid) < 2))
            hotmsg = []
            wordinmsg = lambda x: re_word.search(self.msgs[x][1])
            ranked = uniq(uniq(filter(wordinmsg, map(lambda x: self.fwd_lookup.get(operator.itemgetter(3, 4)(self.msgs[x[0]]), x[0]), self.hotrank(chunk)))), key=lambda x: self.tc.truecase(self.msgs[x][1])) or list(filter(wordinmsg, chunk)) or chunk
            for mid in (ranked[:10] or chunk[:10]):
                msg = self.msgs[mid]
                text = msg[1]
                if len(text) > 500:
                    text = text[:500] + '…'
                hotmsg.append((mid, stripreaction(text), msg[0], db_getfirstname(msg[0], json.loads(msg[6] or '{}')), strftime('%H:%M:%S', msg[2])))
            yield (kwds, hotmsg)

    def tags(self):
        tags = collections.defaultdict(list)
        for mid, value in self.msgs.items():
            text = value[1] or ''
            for tag in re_tag.findall(text):
                tags[self.tc.truecase(tag)].append(mid)
        return sorted(tags.items(), key=lambda x: (-len(x[1]), x[0]))

    def tc_preprocess(self):
        titles = []
        for mid, value in self.msgs.items():
            media = json.loads(value[6] or '{}')
            if 'new_chat_title' in media:
                titles.append((mid, media['new_chat_title']))
        if titles:
            prefix = [os.path.commonprefix([text for mid, text in titles])]
        else:
            prefix = [self.title]
        for mid, text in titles:
            for k in range(len(prefix), -1, -1):
                pf = ''.join(prefix[:k])
                if text.startswith(pf):
                    text = text[len(pf):]
                    prefix = prefix[:k]
                    prefix.append(text)
                    break
            yield (mid, prefix)

    def titlechange(self):
        last = []
        for mid, prefix in self.tc_preprocess():
            comm = os.path.commonprefix((last, prefix))
            if len(prefix) == len(last) == len(comm) + 1:
                yield '<li>'
                msg = self.msgs[mid]
                yield (mid, prefix[-1], msg[0], db_getfirstname(msg[0]), strftime('%H:%M:%S', msg[2]))
                yield '</li>'
            else:
                for k in range(len(last) - len(comm)):
                    yield '</ul>'
                for item in prefix[len(comm):-1]:
                    yield '<ul><li>'
                    yield (mid, item)
                    yield '</li>'
                yield '<ul><li>'
                msg = self.msgs[mid]
                yield (mid, prefix[-1], msg[0], db_getfirstname(msg[0]), strftime('%H:%M:%S', msg[2]))
                yield '</li>'
            last = prefix
        for item in last:
            yield '</ul>'

    def generalinfo(self):
        ctr = collections.Counter(i[0] for i in self.msgs.values())
        mcomm = ctr.most_common(5)
        count = len(self.msgs)
        others = count - sum(v for k, v in mcomm)
        delta = self.end - self.start
        stat = {
            'start': strftime('%d 日 %H:%M:%S', self.start),
            'end': strftime('%d 日 %H:%M:%S', self.end),
            'count': count,
            'freq': '%.2f' % (count * 60 / delta) if delta else 'N/A',
            'flooder': tuple(((k, db_getufname(k)), v, '%.2f%%' % (v/count*100)) for k, v in mcomm),
            'tags': self.tags()[:6],
            'others': (others, '%.2f%%' % (others/count*100)),
            'avg': '%.2f' % (count / len(ctr))
        }
        return stat

    def render(self):
        kvars = {
            'name': NAME,
            'date': strftime('%Y-%m-%d', self.date),
            'wday': getwday(self.date),
            'info': self.generalinfo(),
            'hotchunk': tuple(self.hotchunk()),
            'titlechange': tuple(self.titlechange()),
            'gentime': strftime('%Y-%m-%d %H:%M:%S')
        }
        template = jinja2.Environment(loader=jinja2.FileSystemLoader('templates')).get_template(self.template)
        return template.render(**kvars)

class StatComposer:

    def __init__(self):
        self.template = 'stat.html'
        self.tc = truecaser.Truecaser(truecaser.loaddict(open('vendor/truecase.txt', 'rb')))

    def fetchmsgstat(self):
        self.msglen = self.start = self.end = 0
        hourctr = [0] * 24
        mediactr = collections.Counter()
        usrctr = collections.Counter()
        tags = collections.Counter()
        for mid, src, text, date, media in conn.execute('SELECT id, src, text, date, media FROM messages ORDER BY date ASC, id ASC'):
            text = text or ''
            if not self.start:
                self.start = date
            self.start = min(self.start, date)
            self.end = max(self.end, date)
            for tag in re_tag.findall(text):
                tags[self.tc.truecase(tag)] += 1
            media = json.loads(media or '{}')
            mt = media.keys() & MEDIA_TYPES.keys()
            if mt:
                t = tuple(mt)[0]
            elif media.keys() & SERVICE:
                t = 'service'
            else:
                t = 'text'
            hourctr[int(((date + TIMEZONE) // 3600) % 24)] += 1
            mediactr[t] += 1
            usrctr[src] += 1
            self.msglen += 1
        self.end = date
        typesum = sum(mediactr.values())
        types = [(MEDIA_TYPES[k], '%.2f%%' % (v * 100 / typesum)) for k, v in mediactr.most_common()]
        tags = sorted(filter(lambda x: x[1] > 2, tags.items()), key=lambda x: (-x[1], x[0]))
        return hourctr, types, tags, usrctr

    def generalinfo(self):
        hours, types, tags, usrctr = self.fetchmsgstat()
        hsum = sum(hours)
        hourdist = ['%.2f%%' % (h * 100 / hsum) for h in hours]
        mcomm = usrctr.most_common()
        count = self.msglen
        stat = {
            'start': strftime('%Y-%m-%d %H:%M:%S', self.start),
            'end': strftime('%Y-%m-%d %H:%M:%S', self.end),
            'count': count,
            'freq': '%.2f' % (count * 60 / (self.end - self.start)),
            'flooder': tuple(((k, db_getufname(k)), db_getuser(k)[0] or '', '%.2f%%' % (v/count*100)) for k, v in mcomm if v > 2),
            'hours': hourdist,
            'types': types,
            'tags': tags,
            'avg': '%.2f' % (count / len(usrctr))
        }
        return stat

    def render(self):
        kvars = {
            'name': NAME,
            'info': self.generalinfo(),
            'gentime': strftime('%Y-%m-%d %H:%M:%S')
        }
        template = jinja2.Environment(loader=jinja2.FileSystemLoader('templates')).get_template(self.template)
        return template.render(**kvars)

re_digest = re.compile(r'^(\d+)-(\d+)-(\d+).html$')

class DigestManager:

    def __init__(self, path='.'):
        self.template = 'index.html'
        self.path = path

    def copyresource(self):
        for filename in ('digest.css',):
            src = os.path.join('templates', filename)
            dst = os.path.join(self.path, filename)
            shutil.copyfile(src, dst)
            shutil.copystat(src, dst)

    def writenewdigest(self, date=None, update=False):
        date = date or (time.time() - 86400)
        filename = os.path.join(self.path, strftime('%Y-%m-%d.html', date))
        if not update and os.path.isfile(filename):
            return
        try:
            dc = DigestComposer(date)
        except ValueError:
            return
        dc.title = TITLE
        with open(filename, 'w') as f:
            f.write(dc.render())
        del dc

    def writenewstat(self):
        sc = StatComposer()
        with open(os.path.join(self.path, 'stat.html'), 'w') as f:
            f.write(sc.render())
        del sc

    def genindex(self):
        index = []
        for filename in sorted(os.listdir(self.path), reverse=True):
            fn = re_digest.match(filename)
            if fn:
                index.append((filename, '%s 年 %s 月 %s 日' % fn.groups()))
        return index

    def render(self):
        kvars = {
            'name': NAME,
            'index': self.genindex(),
            'gentime': strftime('%Y-%m-%d %H:%M:%S')
        }
        template = jinja2.Environment(loader=jinja2.FileSystemLoader('templates')).get_template(self.template)
        return template.render(**kvars)

    def writenewindex(self):
        with open(os.path.join(self.path, 'index.html'), 'w') as f:
            f.write(self.render())


if __name__ == '__main__':

    path = '.'
    version = 1
    update = False

    if len(sys.argv) > 1:
        path = sys.argv[1]
    if len(sys.argv) > 2:
        version = int(sys.argv[2])
    if len(sys.argv) > 3:
        update = bool(sys.argv[3])

    start = time.time()
    dm = DigestManager(path)
    dm.copyresource()
    for i in range(1, version+1):
        dm.writenewdigest(start - 86400 * i, update)
    dm.writenewstat()
    dm.writenewindex()
    sys.stderr.write('Done in %.4gs.\n' % (time.time() - start))
