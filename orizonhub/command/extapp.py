#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import imp
import json
import queue
import sqlite3
import tempfile
import resource
import itertools
import threading
import traceback
import subprocess
import collections
import concurrent.futures

from ext import zhutil
from ext import zhconv
from ext import figchar
from ext import simpcalc
from ext import mosesproxy
from ext import chinesename

root_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
main_config = imp.load_module('config', *imp.find_module(
    'config', [root_path])).config

resource.setrlimit(resource.RLIMIT_RSS, (131072, 262144))

# Issue 28985
SQLITE_FUNCTION = 31

def setsplimits(cputime, memory):
    def _setlimits():
        resource.setrlimit(resource.RLIMIT_CPU, cputime)
        resource.setrlimit(resource.RLIMIT_RSS, memory)
        resource.setrlimit(resource.RLIMIT_NPROC, (2048, 2048))
    return _setlimits

# {"id": 1, "cmd": "bf", "args": [",[.,]", "asdasdf"]}

def docommands():
    global MSG_Q
    while 1:
        obj = MSG_Q.get()
        executor.submit(async_command, obj)

def async_command(obj):
    sys.stdout.buffer.write(json.dumps(process(obj)).encode('utf-8') + b'\n')
    sys.stdout.flush()

def getsaying():
    global SAY_P, SAY_Q
    while 1:
        say = getsayingbytext(mode='')
        SAY_Q.put(say)

def getsayingbytext(text='', mode='r'):
    global SAY_P
    with SAY_LCK:
        text = (mode + ' '.join(mosesproxy.cut(zhconv.convert(text, 'zh-hans'), HMM=False)[:60]).strip()).encode('utf-8') + b'\n'
        try:
            SAY_P.stdin.write(text)
            SAY_P.stdin.flush()
            say = SAY_P.stdout.readline().strip().decode('utf-8')
        except BrokenPipeError:
            SAY_P = subprocess.Popen(SAY_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd='ext')
            SAY_P.stdin.write(text)
            SAY_P.stdin.flush()
            say = SAY_P.stdout.readline().strip().decode('utf-8')
    return say

def process(obj):
    ret, exc = None, None
    try:
        ret = COMMANDS[obj['cmd']](*obj['args'])
    except Exception:
        exc = traceback.format_exc()
    return {'id': obj['id'], 'ret': ret, 'exc': exc}

def cmd_calc(expr):
    '''/calc <expr> Calculate <expr>.'''
    r = calculator.pretty(expr)
    if len(r) > 200:
        r = r[:200] + '...'
    return r or 'Nothing'

def cmd_py(expr):
    proc = subprocess.Popen(EVIL_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd='ext', preexec_fn=setsplimits((4, 5), (8192, 16384)))
    try:
        result, errs = proc.communicate(expr.strip().encode('utf-8'), timeout=5)
    except Exception: # TimeoutExpired
        proc.kill()
        result, errs = proc.communicate()
    finally:
        #print(result, errs)
        if proc.poll() is None:
            proc.terminate()
    result = result.strip().decode('utf-8', errors='replace')
    return result or 'None or error occurred.'

def cmd_name(expr):
    surnames, names = namemodel.processinput(expr, 10)
    res = []
    if surnames:
        res.append('姓：' + ', '.join(surnames[:10]))
    if names:
        res.append('名：' + ', '.join(names[:10]))
    return '\n'.join(res)

def cmd_fig(expr):
    r = fcgen.render(expr)
    rl = r.splitlines()
    if not r:
        return 'Missing glyph(s).'
    elif len(rl[0]) < 12 and len(rl) < 15:
        return r
    else:
        return 'Figure too big.'

def cmd_cc(expr):
    if zhconv.issimp(expr):
        return zhconv.convert(expr, 'zh-hant')
    else:
        return zhconv.convert(expr, 'zh-hans')

def cmd_cut(tinput, lang):
    if lang == 'c':
        return ' '.join(mosesproxy.jiebazhc.cut(tinput, HMM=False))
    else:
        return ' '.join(mosesproxy.cut(tinput, HMM=False))

def cmd_wyw(tinput, lang):
    if tinput == '$name':
        return mosesproxy.modelname()
    if lang is None:
        cscore, mscore = zhutil.calctxtstat(tinput)
        if cscore == mscore:
            lang = None
        elif zhutil.checktxttype(cscore, mscore) == 'c':
            lang = 'c2m'
        else:
            lang = 'm2c'
    if lang:
        return mosesproxy.translate(tinput, lang, 0, 0, 0)
    else:
        return tinput

def cmd_say():
    return SAY_Q.get() or 'ERROR_BRAIN_NOT_CONNECTED'

def cmd_reply(expr):
    return getsayingbytext(expr, 'r') or 'ERROR_BRAIN_NOT_CONNECTED'

def cmd_cont(expr):
    return getsayingbytext(expr, 'c') or 'ERROR_BRAIN_NOT_CONNECTED'

def sql_auth(sqltype, arg1, arg2, dbname, source):
    if sqltype in (sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    else:
        return sqlite3.SQLITE_DENY

def cmd_query(expr):
    try:
        conn = sqlite3.connect(os.path.join(root_path, main_config['loggers']['sqlite']))
        conn.set_authorizer(sql_auth)
        cur = conn.cursor()
        cur.execute(expr)
        result = ('|'.join(desc[0] for desc in cur.description) + '\n' + '\n'.join(
                  '|'.join('' if e is None else str(e) for e in r) for r in
                  itertools.islice(cur, 0, 10)))
        conn.close()
        return result
    except sqlite3.DatabaseError as ex:
        return str(ex)

COMMANDS = collections.OrderedDict((
('calc', cmd_calc),
('py', cmd_py),
('name', cmd_name),
('fig', cmd_fig),
('cc', cmd_cc),
('wyw', cmd_wyw),
('cut', cmd_cut),
('say', cmd_say),
('reply', cmd_reply),
('cont', cmd_cont),
('query', cmd_query)
))

MSG_Q = queue.Queue()
SAY_Q = queue.Queue(maxsize=50)
SAY_LCK = threading.Lock()

SAY_CMD = ('python3', 'say.py',
           'data/chat.binlm', 'data/chatdict.txt', 'data/context.pkl')
SAY_P = subprocess.Popen(SAY_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd='ext')

EVIL_CMD = ('python', 'seccomp.py')
LISP_CMD = ('python', 'lispy.py')

executor = concurrent.futures.ThreadPoolExecutor(5)
cmdthr = threading.Thread(target=docommands)
cmdthr.daemon = True
cmdthr.start()

saythr = threading.Thread(target=getsaying)
saythr.daemon = True
saythr.start()

calculator = simpcalc.Calculator('ans', True)
namemodel = chinesename.NameModel('ext/data/namemodel.m')
fcgen = figchar.BlockGenerator('ext/data/wqy.pkl', '🌝🌚')

try:
    for ln in sys.stdin.buffer:
        upd = json.loads(ln.decode('utf-8'))
        MSG_Q.put(upd)
finally:
    SAY_P.terminate()
