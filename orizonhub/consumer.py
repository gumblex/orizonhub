#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shlex
import logging
import collections
import concurrent.futures

import pytz

from .model import Message, Request, Response
from .provider import command

logger = logging.getLogger('msghandler')

class MessageHandler:
    def __init__(self, config, protocols, loggers):
        logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.config = config
        self.protocols = protocols
        self.loggers = loggers
        self.providers = collections.ChainMap(self.protocols, self.loggers)
        self.executor = concurrent.futures.ThreadPoolExecutor(10)
        self.timezone = pytz.timezone(config.timezone)
        self.usernames = [p.username for p in config.protocols.values()
                          if 'username' in p]

    def __call__(self, msg):
        logger.debug(msg)
        if isinstance(msg, Request):
            return self.dispatch(msg)
        else:
            if msg.mtype == 'group':
                for n, l in self.loggers.items():
                    self.executor.submit(l.log, (msg,))
                for n in self.config.forward:
                    if n != msg.protocol:
                        self.executor.submit(self.protocols[n].forward, (msg, n))
            req = self.parse_cmd(msg.text) if msg.text else None
            if req:
                logger.debug('parsed request: %s', req)
                return self.dispatch(req, msg)
            else:
                return self.dispatch_gh(msg)

    def respond(self, res):
        for n, p in self.protocols.items():
            if (n == self.config.main_protocol
                and res.reply and res.reply.mtype == 'group'):
                fut = self.executor.submit(p.send, (res,))
                fut.add_done_callback(self._resp_log_cb)
            else:
                self.executor.submit(p.send, (res,))

    def _resp_log_cb(fut):
        msg = fut.result()
        for n, l in self.loggers.items():
            self.executor.submit(l.log, (msg,))

    def parse_cmd(self, text):
        t = text.strip().split(' ', 1)
        if not t:
            return None
        cmd = t[0].rsplit('@', 1)
        if len(cmd[0]) < 2 or cmd[0][0] not in command.PREFIX:
            return None
        if len(cmd) > 1 and cmd[-1] not in self.usernames:
            return None
        expr = t[1] if len(t) > 1 else ''
        return Request(cmd[0][1:], expr, {})

    def dispatch(self, req, msg=None):
        c = command.commands.get(req.cmd)
        logger.debug('command: %s', c)
        if not (c is None
                or msg is None and c.protocol
                or c.protocol and msg.protocol not in c.protocol
                or c.dependency and c.dependency not in self.providers):
            if msg:
                req.kwargs['msg'] = msg
            r = c.func(req.expr, **req.kwargs)
            logger.debug('response: %s', r)
            if r:
                if not isinstance(r, Response):
                    r = Response(r, None, msg)
                return r

    def dispatch_gh(self, msg):
        '''
        Dispatch general handlers. Only return the first answer.
        '''
        for gh in command.general_handlers.values():
            if not (gh.protocol and msg.protocol not in gh.protocol
                    or gh.dependency and gh.dependency not in self.providers):
                r = gh.func(msg)
                if r:
                    if not isinstance(r, Response):
                        r = Response(r, None, msg)
                    return r
