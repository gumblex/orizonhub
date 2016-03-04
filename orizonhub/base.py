#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import collections

from . import utils, provider
from .model import __version__
from .consumer import MessageHandler

import pytz

class BotInstance:
    def __init__(self, config):
        self.config = config = utils.wrap_attrdict(config)
        self.timezone = pytz.timezone(config.timezone)

        self.commands = collections.OrderedDict()
        self.protocols = {}
        self.loggers = {}
        self.threads = []

        self.bus = MessageBus(MessageHandler(config, self.protocols, self.loggers))
        self.bus.timezone = self.timezone
        provider.command.bus = self.bus
        logging.info('Bot instance initialized.')

    def start(self):
        services = self.config.services
        if services.pastebin == 'self':
            self.bus.pastebin = provider.SimplePasteBin(services.cachepath, services.get('maxsize', 1048576), services.mediaurl)
        elif services.pastebin == 'vim-cn':
            self.bus.pastebin = provider.VimCN(services.cachepath)
        for k, v in self.config.loggers.items():
            try:
                self.loggers[k] = provider.loggers[k](v, self.timezone)
                logging.info('Registered logging: ' + k)
            except KeyError:
                raise ValueError('unrecognized logging: ' + k)
        if self.config.status == ':SQLite3:':
            self.bus.state = provider.SQLiteStateStore(self.loggers['sqlite'].conn)
        else:
            self.bus.state = provider.BasicStateStore(self.config.status)
        for k, v in self.config.protocols.items():
            try:
                if v.get('enabled', True):
                    p = self.protocols[k] = provider.protocols[k](self.config, self.bus)
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
            v.close()
        self.bus.close()
        for v in self.loggers.values():
            v.close()
        logging.info('Exited cleanly.')

class MessageBus:
    def __init__(self, handler):
        self.handler = handler
        self.pastebin = provider.DummyPasteBin()
        self.state = {}
        self.timezone = None

    def post(self, msg):
        return self.handler(msg)

    def post_sync(self, msg):
        return self.handler(msg, False).result()

    def close(self):
        if self.state:
            self.state.close()
        self.pastebin.close()

    def __getattr__(self, name):
        try:
            return self.handler.providers[name]
        except KeyError:
            raise AttributeError("handler %r not found" % name)
