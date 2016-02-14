#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
from datetime import datetime
from logging.handlers import WatchedFileHandler

class Logger:
    pass

class TextLogger:

    FORMAT = '%(asctime)s [%(protocol)s:%(pid)d] %(srcname)s >> %(text)s'

    def __init__(self, filename, tz):
        self.logger = logging.getLogger('chatlog')
        self.logger.setLevel(logging.INFO)
        self.loghandler = WatchedFileHandler(filename, encoding='utf-8', delay=True)
        self.loghandler.setLevel(logging.INFO)
        self.loghandler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(self.loghandler)
        self.tz = tz

    def log(msg):
        d = msg._asdict()
        d['asctime'] = datetime.fromtimestamp(msg.time, self.tz).strftime('%Y-%m-%d %H:%M:%S')
        d['srcname'] = msg.src.

logging.handlers.WatchedFileHandler
