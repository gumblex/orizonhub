#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import queue
import logging
import threading
import collections
import concurrent.futures

from . import utils, provider
from .model import User
from .consumer import MessageHandler

import pytz

__version__ = '2.0'

class BotInstance:
    def __init__(self, config):
        self.config = config = utils.wrap_attrdict(config)
        self.logger = logging.getLogger('orizond')
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.executor = concurrent.futures.ThreadPoolExecutor(10)
        self.timezone = pytz.timezone(config.timezone)
        self.identity = User(0, 'bot', 0, config.bot_nickname, config.bot_fullname, None, config.bot_nickname)

        self.commands = collections.OrderedDict()
        self.protocols = {}
        self.loggers = {}
        self.providers = collections.ChainMap(self.protocols, self.loggers)
        self.threads = []
        self.state = {}

        self.bus = MessageBus(MessageHandler(config, self.protocols))
        self.logger.info('Bot instance initialized.')

    def start(self):
        for k, v in self.config.loggers.items():
            try:
                self.loggers[k] = provider.loggers[k](v, self.timezone)
                self.logger.info('Registered logger: ' + k)
            except KeyError:
                raise ValueError('unrecognized logger: ' + k)
        if self.config.status == ':SQLite3:':
            self.state = provider.SQLiteStateStore(self.loggers['sqlite'].conn)
        else:
            self.state = provider.BasicStateStore(self.config.status)
        for k, v in self.config.protocols.items():
            try:
                if v.get('enabled', True):
                    p = self.protocols[k] = provider.protocols[k](v, self.identity, self.bus)
                    t = threading.Thread(target=p.start_polling, name=k)
                    t.daemon = True
                    t.start()
                    self.logger.info('Started protocol: ' + k)
                    self.threads.append(t)
            except KeyError:
                raise ValueError('unrecognized logger: ' + v)
        self.logger.info('Satellite launched.')
        for t in self.threads:
            try:
                t.join()
            except KeyboardInterrupt:
                self.logger.warning('Thread "%s" died with ^C.' % t.name)

    def exit(self):
        for v in self.protocols.values():
            v.exit()
        self.state.close()
        for v in self.loggers.values():
            v.close()
        self.logger.info('Exited cleanly.')

    def submit_task(self, func, *args, **kwargs):
        return self.executor.submit(func, *args, **kwargs)

class MessageBus:
    def __init__(self, handler):
        self.msg_q = queue.Queue()
        self.handler = handler

    def post(self, msg):
        self.msg_q.put(msg)

    def post_sync(self, msg):
        self.msg_q.put(msg)

    def stream(self):
        while 1:
            m = self.msg_q.get()
            if m is None:
                return
            yield m
