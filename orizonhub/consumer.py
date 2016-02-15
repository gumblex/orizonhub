#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shlex
from . import base
from .provider import command

import pytz

class MessageHandler:
    def __init__(self, config, protocols):
        self.config = config
        self.protocols = protocols
        self.timezone = pytz.timezone(config.timezone)
        self.usernames = [p.username for p in config.protocols.values()
                          if 'username' in p]

    def __call__(self, msg):
        ...

    def parse_cmd(self, text):
        t = shlex.split(text.strip())
        if not t:
            return None
        cmd = t[0].rsplit('@', 1)
        if len(cmd[0]) < 2 or cmd[0][0] not in command.PREFIX:
            return None
        if len(cmd) > 1 and cmd[-1] not in self.usernames:
            return None
        return cmd[0][1:], t[1:]

    def dispatch(self, cmd, args):
        ...

    def forward(self, msg):
        ...
