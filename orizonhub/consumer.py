#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
import collections
import concurrent.futures

import pytz

from .model import Message, User, Request, Response
from .utils import nt_repr
from .provider import command

logger = logging.getLogger('handler')

class MessageHandler:
    def __init__(self, config, protocols, loggers):
        # logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.config = config
        self.protocols = protocols
        self.loggers = loggers
        self.providers = collections.ChainMap(self.protocols, self.loggers)
        self.executor = concurrent.futures.ThreadPoolExecutor(10)
        self.timezone = pytz.timezone(config.timezone)
        self.usernames = set(p.username for p in config.protocols.values()
                             if 'username' in p)
        self.messagettl = 120

    def process(self, msg):
        #logger.debug(nt_repr(msg))
        now = time.time()
        tasks = {}
        logger.info('Message: ' + msg.text)
        if isinstance(msg, Request):
            return tasks, self.dispatch(msg)
        else:
            if msg.mtype == 'group':
                for n, l in self.loggers.items():
                    tasks[n] = self.submit_task(l.log, msg)
                if self.messagettl + msg.time > now:
                    for n in self.config.forward:
                        if n != msg.protocol and n in self.protocols:
                            tasks[n] = self.submit_task(
                                self.protocols[n].forward, msg, n)
            if self.messagettl + msg.time > now:
                req = self.parse_cmd(msg.text) if msg.text else None
                if req:
                    logger.debug('parsed request: %s', req)
                    return tasks, self.dispatch(req, msg)
                else:
                    return tasks, self.dispatch_gh(msg)
            else:
                logger.debug('ignored old message(%s): %s', msg.time, msg.text)
        return tasks, None

    def respond(self, res, processed={}):
        # res.reply must be Message
        if res.reply.mtype == 'group':
            for n, p in self.protocols.items():
                if n == self.config.main_protocol:
                    fut = self.submit_task(p.send, res, n, processed.get(n))
                    fut.add_done_callback(self._resp_log_cb)
                else:
                    self.submit_task(p.send, res, n, processed.get(n))
        else:
            pn = res.reply.protocol
            self.submit_task(self.protocols[pn].send, res, pn, None)

    def __call__(self, msg, respond=True):
        def _do_process(msg, respond):
            try:
                tasks, r = self.process(msg)
            except Exception:
                logger.exception('Failed to process a message: %s', msg)
            if respond and r:
                try:
                    self.respond(r, tasks)
                except Exception:
                    logger.exception('Failed to respond to a message: %s', r)
            else:
                return r
        return self.executor.submit(_do_process, msg, respond)

    def status(self, dest: User, action: str):
        for n, p in self.protocols.items():
            self.submit_task(p.status, dest, action)

    def _resp_log_cb(self, fut):
        msg = fut.result()
        if msg is None:
            logger.warning('%s.send() returned None', self.config.main_protocol)
            return
        for n, l in self.loggers.items():
            self.submit_task(l.log, msg)

    def parse_cmd(self, text: str):
        t = text.strip().replace('\xa0', ' ').split(' ', 1)
        if not t:
            return None
        cmd = t[0].rsplit('@', 1)
        if len(cmd[0]) < 2 or cmd[0][0] not in command.PREFIX:
            return None
        if len(cmd) > 1 and cmd[-1] not in self.usernames:
            return None
        expr = t[1] if len(t) > 1 else ''
        return Request(cmd[0][1:], expr, {})

    def dispatch(self, req: Request, msg=None):
        c = command.commands.get(req.cmd)
        logger.debug('command: %s', c)
        if not (c is None
                or msg is None and c.protocol
                or c.protocol and msg.protocol not in c.protocol
                or c.mtype and msg.mtype not in c.mtype
                or c.dependency and c.dependency not in self.providers
            ):
            if msg:
                req.kwargs['msg'] = msg
            elif 'msg' in req.kwargs:
                # no fake messages
                del req.kwargs['msg']
            try:
                r = c.func(req.expr, **req.kwargs)
            except Exception:
                logger.exception('Failed to execute: %s', req)
                return None
            logger.debug('response: %s', r)
            if r:
                if not isinstance(r, Response):
                    r = Response(r, None, msg)
                return r

    def dispatch_gh(self, msg: Message):
        '''
        Dispatch general handlers. Only return the first answer.
        '''
        for gh in command.general_handlers.values():
            if not (gh.protocol and msg.protocol not in gh.protocol
                    or gh.dependency and gh.dependency not in self.providers):
                try:
                    r = gh.func(msg)
                except Exception:
                    logger.exception('Failed to execute general handler: %s', gh)
                    continue
                if r:
                    if not isinstance(r, Response):
                        r = Response(r, None, msg)
                    return r

    def submit_task(self, fn, *args, **kwargs):
        def func_noerr(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                logger.exception('Async function failed.')
        return self.executor.submit(func_noerr, *args, **kwargs)

    def close(self):
        self.executor.shutdown()
