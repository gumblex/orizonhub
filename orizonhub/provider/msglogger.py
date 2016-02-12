#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sqlite3
from .base import *

TG_EXT_MEDIA_TYPES = frozenset(('audio', 'document', 'photo', 'sticker', 'video', 'voice', 'contact', 'location', 'new_chat_participant', 'left_chat_participant', 'new_chat_title', 'new_chat_photo', 'delete_chat_photo', 'group_chat_created', '_ircuser'))

class SimpleLogger(MessageLogger):
    name = 'simple'
    def onmsg(self, msg):
        logging.info('Msg: %s' % msg)

class SQLiteLogger(MessageLogger):
    name = 'sqlite'
    def __init__(self, db):
        self.user_cache = LRUCache(20)
        self.msg_cache = LRUCache(10)
        self.db = sqlite3.connect(db)
        conn = self.db.cursor()
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
        uid INTEGER PRIMARY KEY,
        id INTEGER,
        src INTEGER,
        dest INTEGER,
        text TEXT,
        media TEXT,
        date INTEGER,
        fwd_src INTEGER,
        fwd_date INTEGER,
        reply_id INTEGER
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT
        )''')
        conn.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, val INTEGER)')

    def teardown(self):
        self.commit()

    def adduser(self, d):
        conn = self.db.cursor()
        user = (d['id'], d.get('username'), d.get('first_name'), d.get('last_name'))
        conn.execute('REPLACE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)', user)
        self.user_cache[d['id']] = (d.get('username'), d.get('first_name'), d.get('last_name'))
        return user

    def logmsg(self, d, iorignore=False):
        conn = self.db.cursor()
        src = self.adduser(d['from'])[0]
        text = d.get('text') or d.get('caption', '')
        media = {k:d[k] for k in TG_EXT_MEDIA_TYPES.intersection(d.keys())}
        fwd_src = self.adduser(d['forward_from'])[0] if 'forward_from' in d else None
        reply_id = d['reply_to_message']['message_id'] if 'reply_to_message' in d else None
        into = 'INSERT OR IGNORE INTO' if iorignore else 'REPLACE INTO'
        conn.execute(into + ' messages (id, src, text, media, date, fwd_src, fwd_date, reply_id) VALUES (?,?,?,?, ?,?,?,?)',
                     (d['message_id'], src, text, json.dumps(media) if media else None, d['date'], fwd_src, d.get('forward_date'), reply_id))
        logging.info('Logged %s: %s', d['message_id'], d.get('text', '')[:15])

    def execute(self, *args, **kwargs):
        conn = self.db.cursor()
        return self.conn.execute(*args, **kwargs)

    def commit(self):
        return self.db.commit()

    def onmsg(self, msg):
        ...

