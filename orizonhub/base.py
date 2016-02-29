#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import queue
import logging
import threading
import collections

from . import utils, provider
from .consumer import MessageHandler

import pytz

__version__ = '2.0'

class BotInstance:
    def __init__(self, config):
        self.config = config = utils.wrap_attrdict(config)
        self.timezone = pytz.timezone(config.timezone)

        self.commands = collections.OrderedDict()
        self.protocols = {}
        self.loggers = {}
        self.threads = []
        self.state = {}

        self.bus = MessageBus(MessageHandler(config, self.protocols, self.loggers))
        logging.info('Bot instance initialized.')

    def start(self):
        services = self.config.services
        if services.pastebin == 'self':
            self.pastebin = provider.SimplePasteBin(services.cachepath, services.mediaurl)
        elif services.pastebin == 'vim-cn':
            self.pastebin = provider.VimCN(services.cachepath)
        else:
            self.pastebin = provider.DummyPasteBin()
        for k, v in self.config.loggers.items():
            try:
                self.loggers[k] = provider.loggers[k](v, self.timezone)
                logging.info('Registered logging: ' + k)
            except KeyError:
                raise ValueError('unrecognized logging: ' + k)
        if self.config.status == ':SQLite3:':
            self.state = provider.SQLiteStateStore(self.loggers['sqlite'].conn)
        else:
            self.state = provider.BasicStateStore(self.config.status)
        for k, v in self.config.protocols.items():
            try:
                if v.get('enabled', True):
                    p = self.protocols[k] = provider.protocols[k](self.config, self.bus, self.pastebin)
                    for proxy in v.get('proxies') or ():
                        self.protocols[proxy[0]] = p
                    t = threading.Thread(target=p.start_polling, name=k)
                    t.daemon = True
                    t.start()
                    logging.info('Started protocol: ' + k)
                    self.threads.append(t)
            except KeyError:
                raise ValueError('unrecognized protocol: ' + v)
        logging.info('Satellite launched.')
        try:
            for t in self.threads:
                t.join()
        except KeyboardInterrupt:
            logging.warning('SIGINT received.')

    def exit(self):
        for v in self.protocols.values():
            v.exit()
        if self.state:
            self.state.close()
        for v in self.loggers.values():
            v.close()
        logging.info('Exited cleanly.')

class MessageBus:
    def __init__(self, handler):
        self.handler = handler

    def post(self, msg):
        return self.handler(msg)

    def post_sync(self, msg):
        return self.handler(msg, False).result()
