#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import queue
import sqlite3
import logging
import threading
import collections
from datetime import datetime, timezone
from logging.handlers import WatchedFileHandler

from .utils import LRUCache, nt_repr
from .model import Message, User, Logger

logger = logging.getLogger('logger')

class TextLogger(Logger):
    '''Logs messages with plain text. Rotating-friendly.'''
    FORMAT = '%(asctime)s [%(protocol)s:%(pid)s] %(srcname)s >> %(text)s'

    def __init__(self, filename, tz=timezone.utc):
        self.loghandler = WatchedFileHandler(filename, encoding='utf-8', delay=True)
        self.loghandler.setLevel(logging.INFO)
        self.loghandler.setFormatter(logging.Formatter('%(message)s'))
        self.tz = tz

    def log(self, msg: Message):
        d = msg._asdict()
        d['asctime'] = datetime.fromtimestamp(msg.time, self.tz).strftime('%Y-%m-%d %H:%M:%S')
        d['srcname'] = msg.src.alias
        d['srcid'] = msg.src.id
        self.loghandler.emit(logging.makeLogRecord({'msg': self.FORMAT % d}))

class SQLiteLogger(Logger):
    '''Logs messages with SQLite.'''
    SCHEMA = (
        'CREATE TABLE IF NOT EXISTS messages ('
            'id INTEGER PRIMARY KEY,'
            'protocol TEXT NOT NULL,'
            'pid INTEGER,'
            'src INTEGER,'
            'dest INTEGER,'
            'text TEXT,'
            'media TEXT,'
            'time INTEGER,'
            'fwd_src INTEGER,'
            'fwd_time INTEGER,'
            'reply_id INTEGER,'
            'FOREIGN KEY (src) REFERENCES users(id),'
            # For the purposes of UNIQUE constraints, NULL values are considered
            # distinct from all other values, including other NULLs.
            'UNIQUE (protocol, pid)'
        ')',
        'CREATE TABLE IF NOT EXISTS users ('
            'id INTEGER PRIMARY KEY,'
            'protocol TEXT NOT NULL,'
            'type INTEGER NOT NULL,'
            'pid INTEGER,'  # protocol-specified id
            'username TEXT,'
            'first_name TEXT,'
            'last_name TEXT,'
            'alias TEXT,'
            'UNIQUE (protocol, type, pid, username)'
        ')',
    )

    def __init__(self, filename, tz=None, wal=True, autocommit=True):
        self.lock = threading.Lock()
        self.autocommit = autocommit
        self.msg_cache = LRUCache(50)
        self.user_cache = {}
        with self.lock:
            self.conn = sqlite3.connect(filename, check_same_thread=False)
            cur = self.conn.cursor()
            for c in self.SCHEMA:
                cur.execute(c)
            self.conn.commit()
            if wal:
                cur.execute('PRAGMA journal_mode=WAL')
            for row in cur.execute('SELECT * FROM users'):
                u = User._make(row)
                self.user_cache[u.id] = self.user_cache[u._key()] = u

    def log(self, msg: Message):
        assert msg.mtype == 'group'
        with self.lock:
            cur = self.conn.cursor()
            dest = self.update_user(msg.chat, cur).id
            src = self.update_user(msg.src, cur).id
            fwd_src = self.update_user(msg.fwd_src, cur).id if msg.fwd_src else None
            try:
                cur.execute('INSERT INTO messages (protocol, pid, src, dest, text, media, time, fwd_src, fwd_time, reply_id) VALUES (?,?,?,?,?, ?,?,?,?,?)', (msg.protocol, msg.pid, src, dest, msg.text, json.dumps(msg.media) if msg.media else None, msg.time, fwd_src, msg.fwd_time, msg.reply and msg.reply.pid))
                self.msg_cache[cur.lastrowid] = msg
            except sqlite3.IntegrityError:
                #logger.warning('Conflict message: %s', nt_repr(msg))
                pass
            if self.autocommit:
                self.conn.commit()

    def update_user(self, user: User, cur):
        '''
        Update user in database if necessary, returns a User with `id` set.

        Consider these situations:
                      In cache        Not in cache
        Known ID       Check         Cache & Update
        Unknown    Get ID & Check   Check, Update/New
        '''
        def _get_user_id(user):
            if user.pid:
                res = cur.execute('SELECT id FROM users WHERE protocol=? AND type=? AND pid=?', (user.protocol, int(user.type), user.pid)).fetchone()
            else:
                res = cur.execute('SELECT id FROM users WHERE protocol=? AND type=? AND pid=? AND username=?', (user.protocol, int(user.type), 0, user.username or '')).fetchone()
            if res:
                return res[0]

        def _update_user(uk, user):
            cur.execute('UPDATE users SET protocol=?, username=?, first_name=?, last_name=?, alias=? WHERE id=?', (user.protocol, user.username or '', user.first_name, user.last_name, user.alias, user.id))
            self.user_cache[user.id] = self.user_cache[uk] = user

        def _new_user(uk, user):
            try:
                cur.execute('INSERT INTO users (protocol, type, pid, username, first_name, last_name, alias) VALUES (?,?,?,?,?,?,?)', (user.protocol, user.type, user.pid or 0, user.username or '', user.first_name, user.last_name, user.alias))
                self.conn.commit()
                uid = cur.lastrowid
            except sqlite3.IntegrityError:
                logger.warning('Conflict user: %s', user)
                uid = _get_user_id(user)
                assert uid
            self.user_cache[uid] = self.user_cache[uk] = User(uid, *user[1:])
            return self.user_cache[uid]

        uk = user._key()
        cached = self.user_cache.get(uk)
        ret = user

        if user.id is None:
            # Cache hit, check and update
            if cached:
                ret = User(cached.id, *user[1:])
                if cached != ret:
                    _update_user(uk, ret)
            # Cache miss, get id or create new
            else:
                uid = _get_user_id(user)
                if uid is None:
                    ret = _new_user(uk, user)
        elif cached != user:
            _update_user(uk, user)
        return ret

    def getuser(self, uid: int):
        try:
            return self.user_cache[uid]
        except KeyError:
            cur = self.conn.cursor()
            u = User._make(cur.execute('SELECT * FROM users WHERE id = ?',
                           (uid,)).fetchone())
            self.user_cache[u.id] = self.user_cache[u._key()] = u
            return u

    def getmsg(self, mid: int):
        res = self.msg_cache.get(mid)
        if res:
            return res
        cur = self.conn.cursor()
        res = cur.execute('SELECT protocol, pid, src, dest, text, media, time, fwd_src, fwd_time, reply_id FROM messages WHERE id = ?', (mid,)).fetchone()
        if res is None:
            return None
        protocol, pid, src, dest, text, media, time, fwd_src, fwd_time, reply_id = res
        msg = Message(
            mid, protocol, pid, self.getuser(src), self.getuser(dest), text,
            media and json.loads(media), time, fwd_src and self.getuser(fwd_src),
            fwd_time, reply_id and self.getmsg(reply_id), 'group', None
        )
        self.msg_cache[mid] = msg
        return msg

    def select(self, req, arg=None):
        cur = self.conn.cursor()
        return cur.execute(req, arg)

    def commit(self):
        try:
            self.conn.commit()
        except sqlite3.OperationalError:
            # sqlite3.OperationalError: cannot commit - no transaction is active
            pass
        logger.debug('db committed.')

    def close(self):
        self.commit()
        self.conn.close()

class BasicStateStore(collections.UserDict):
    def __init__(self, filename):
        if os.path.isfile(filename):
            data = json.load(open(self.filename, 'r', encoding='utf-8'))
            super().__init__(data)
        self.filename = filename

    def commit(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, sort_keys=True, indent=4)

    def close(self):
        self.commit()

class SQLiteStateStore(BasicStateStore):
    def __init__(self, connection, lock):
        self.conn = connection
        self.lock = lock
        with self.lock:
            cur = self.conn.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT)')
            self.conn.commit()
            data = {k: json.loads(v) for k,v in cur.execute('SELECT key, value FROM state')}
        super(BasicStateStore, self).__init__(data)

    def commit(self):
        with self.lock:
            cur = self.conn.cursor()
            for k, v in self.data.items():
                cur.execute('REPLACE INTO state (key, value) VALUES (?,?)', (k, json.dumps(v)))
            self.conn.commit()

    def close(self):
        self.commit()
