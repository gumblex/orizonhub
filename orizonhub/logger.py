#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import logging
import sqlite3
import collections
from datetime import datetime
from logging.handlers import WatchedFileHandler

from .provider.sqlitedict import SqliteMultithread

class Logger:
    def log(self, msg):
        raise NotImplementedError

    def commit(self):
        pass

class TextLogger(Logger):
    '''Logs messages with plain text. Rotating-friendly.'''
    FORMAT = '%(asctime)s [%(protocol)s:%(pid)d] %(srcname)s >> %(text)s'

    def __init__(self, filename, tz):
        self.logger = logging.getLogger('chatlog')
        self.logger.setLevel(logging.INFO)
        self.loghandler = WatchedFileHandler(filename, encoding='utf-8', delay=True)
        self.loghandler.setLevel(logging.INFO)
        self.loghandler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(self.loghandler)
        self.tz = tz

    def log(self, msg):
        d = msg._asdict()
        d['asctime'] = datetime.fromtimestamp(msg.time, self.tz).strftime('%Y-%m-%d %H:%M:%S')
        d['srcname'] = msg.src.alias
        d['srcid'] = msg.src.id
        self.logger.info(self.FORMAT % d)

class SQLiteLogger(Logger):
    '''Logs messages with SQLite.'''
    SCHEMA = (
        'CREATE TABLE IF NOT EXISTS messages ('
            'id INTEGER PRIMARY KEY,'
            'protocol TEXT NOT NULL,'
            'pid INTEGER,'
            'src INTEGER,'
            'text TEXT,'
            'media TEXT,'
            'time INTEGER,'
            'fwd_src INTEGER,'
            'fwd_date INTEGER,'
            'reply_id INTEGER,'
            'FOREIGN KEY(src) REFERENCES users(id)'
        ')',
        'CREATE TABLE IF NOT EXISTS user ('
            'id INTEGER PRIMARY KEY,'
            'protocol TEXT NOT NULL,'
            'pid INTEGER, -- protocol-specified id'
            'username TEXT,'
            'first_name TEXT,'
            'last_name TEXT,'
            'alias TEXT UNIQUE'
        ')'
    )

    def __init__(self, filename):
        self.db = SqliteMultithread(filename)
        cur = self.db.cursor()
        for c in self.SCHEMA:
            cur.execute(c)


class BasicStateStore(collections.UserDict):
    def 



