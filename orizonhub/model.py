#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import collections

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
    'reply'     # Reply message: Message or None
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

Command = collections.namedtuple('Command',
                                 ('func', 'usage', 'protocol', 'dependency'))
Response = collections.namedtuple('Response', ('text', 'info', 'reply'))

class Logger:
    def log(self, msg):
        pass

    def update_user(self, user):
        pass

    def commit(self):
        pass

    def close(self):
        pass

class Protocol:
    def __init__(self, config, identity, bus):
        self.config = config
        self.identity = identity
        self.bus = bus

    def start_polling(self):
        pass

    def send(self, response):
        raise NotImplementedError

    def forward(self, msg):
        raise NotImplementedError

    def exit(self):
        pass
