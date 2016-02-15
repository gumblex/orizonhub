#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import queue
import logging
import collections
import concurrent.futures

from . import utils

__version__ = '2.0'

Message = collections.namedtuple('Message', (
    # Protocol in User use 'telegrambot' and 'telegramcli' because of
    # incompatible 'media' format
    'protocol', # Protocol name: str ('telegrambot', 'irc', ...)
    'pid',      # Protocol-specified message id: int or None
    'src',      # 'From' field: User
    'text',     # Message text: str or None
    'media',    # Extra information about media and service info: dict or None
    'time',     # Message time or receive time: int (unix timestamp)
    'fwd_src',  # Forwarded from (Telegram): User or None
    'fwd_date', # Forwarded message time (Telegram): int (unix timestamp) or None
    'reply'     # Reply message id: Message or None
))

Request = collections.namedtuple('Request', ('cmd', 'args', 'kwargs'))

class User(collections.namedtuple('User', (
        'id',         # User id as in database: int or None (unknown)
        # Protocol in User use 'telegram' as general name
        'protocol',   # Protocol name: str ('telegram', 'irc', ...)
        'pid',        # Protocol-specified message id: int or None
        'username',   # Protocol-specified username: str or None
        'first_name', # Protocol-specified first name or full name: str or None
        'last_name',  # Protocol-specified last name: str or None
        'alias'       # Canonical name alias: str
    ))):
    UnameKey = collections.namedtuple('UnameKey', ('protocol', 'username'))
    PidKey = collections.namedtuple('PidKey', ('protocol', 'pid'))
    def _key(self):
        if self.pid is None:
            return self.UnameKey(self.protocol, self.username)
        else:
            return self.PidKey(self.protocol, self.pid)

class BotInstance:
    def __init__(self, config):
        self.config = utils.wrap_attrdict(config)
        self.logger = logging.getLogger('orizond')
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.executor = concurrent.futures.ThreadPoolExecutor(10)

        self.commands = collections.OrderedDict()
        self.protocols = {}
        self.loggers = {}
        self.providers = collections.ChainMap(self.protocols, self.loggers)

        self.bus = MessageBus()

    def start(self):
        for k, v in self.config.loggers.items():
            pass

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

class Protocol:
    def start_polling(self):
        raise NotImplementedError

    def send(self, text):
        raise NotImplementedError

    def forward(self, msg):
        raise NotImplementedError
