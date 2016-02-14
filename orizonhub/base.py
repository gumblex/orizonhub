#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import queue
import logging
import collections
import concurrent.futures

import pytz

from . import utils

__version__ = '2.0'

Message = collections.namedtuple('Message', (
    # Protocol in User use 'telegrambot' and 'telegramcli' because of
    # incompatible 'media' format
    'protocol', # Protocol name: str ('telegrambot', 'irc', ...)
    'pid',      # Protocol-specified message id: int or None
    'src',      # 'From' field: User
    'text',     # Message text: str
    'media',    # Extra information about media and service info: dict
    'time',     # Message time or receive time: int (unix timestamp)
    'fwd_src',  # Forwarded from (Telegram): User
    'fwd_date', # Forwarded message time (Telegram): int (unix timestamp)
    'reply_id'  # Reply message id: int (-> pid field)
))

User = collections.namedtuple('User', (
    'id',         # User id as in database: int
    # Protocol in User use 'telegram' as general name
    'protocol',   # Protocol name: str ('telegram', 'irc', ...)
    'pid',        # Protocol-specified message id: int or None
    'username',   # Protocol-specified username: str or None
    'first_name', # Protocol-specified first name or full name: str or None
    'last_name',  # Protocol-specified last name: str or None
    'alias'       # Canonical name alias: str
))

class BotInstance:
    def __init__(self, config):
        self.config = utils.wrap_attrdict(config)
        self.logger = logging.getLogger('orizond')
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)

        self.timezone = pytz.timezone(config.timezone)
        self.executor = concurrent.futures.ThreadPoolExecutor(10)

        self.commands = collections.OrderedDict()
        self.protocols = {}
        self.loggers = {}
        self.providers = collections.ChainMap(self.protocols, self.loggers)

        self.msg_q = queue.Queue()

    def start(self):
        for k, v in self.config.loggers.items():
            pass

    def post(self, msg):
        self.msg_q.put(msg)

    def stream(self):
        while 1:
            m = self.msg_q.get()
            if m is None:
                return
            yield m

    def submit_task(self, func, *args, **kwargs):
        return self.executor.submit(func, *args, **kwargs)

class Protocol:
    def start_polling(self):
        raise NotImplementedError

    def send(self, text):
        raise NotImplementedError

    def forward(self, msg):
        raise NotImplementedError
