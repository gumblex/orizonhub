#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import logging

from ..model import Protocol, Message, User
from .libirc import IRCConnection

re_ircfmt = re.compile('[\x02\x1D\x1F\x16\x0F]|\x03(?:\d+(?:,\d+)?)?')
re_ircaction = re.compile('^\x01ACTION (.*)\x01$')

class IRCProtocol(Protocol):
    def __init__(self, config, bus):
        self.config = config
        self.cfg = config.protocols.irc
        self.bus = bus
        self.ircconn = None
        self.run = True
        self.identity = User(None, 'irc', 'user', None, self.cfg.username,
                             config.bot_fullname, None, config.bot_nickname)
        self.dest = User(None, 'irc', 'group', None, self.cfg.channel,
                         self.cfg.channel, None, config.group_name)
        self.proxies = [(p, re.compile(n), re.compile(m)) for p, n, m in self.cfg.proxies]

    def checkircconn(self):
        if self.ircconn and self.ircconn.sock:
            return
        self.ircconn = IRCConnection()
        self.ircconn.connect((self.cfg.server, self.cfg.port), use_ssl=self.cfg.ssl)
        if self.cfg.get('password'):
            self.ircconn.setpass(self.cfg.password)
        self.ircconn.setnick(self.cfg.username)
        self.ircconn.setuser(self.cfg.username, self.cfg.username)
        self.ircconn.join(self.cfg.channel)
        logging.info('IRC (re)connected.')

    def start_polling(self):
        while self.run:
            self.checkircconn()
            line = self.ircconn.parse(block=False)
            mtime = int(time.time())
            logging.debug('IRC: %s', line)
            if not line:
                pass
            elif line["cmd"] == "JOIN" and line["nick"] == self.cfg.username:
                logging.info('I joined IRC channel: %s' % line['dest'])
            elif line["cmd"] == "PRIVMSG":
                # ignored users
                if self.cfg.ignore and re.match(self.cfg.ignore, line["nick"]):
                    continue
                if line["dest"] == self.cfg.username:
                    mtype = 'private'
                    dest = self.identity
                elif line["dest"] == self.cfg.channel:
                    mtype = 'group'
                    dest = self.dest
                else:
                    continue
                # should use /whois and cache to get realname?
                protocol = 'irc'
                src = self._make_user(line["nick"])
                action = re_ircaction.match(line["msg"])
                if action:
                    text = action.group(1)
                    media = {'action': True}
                else:
                    text = line["msg"]
                    media = None
                # OrzTox bot have actions and quotes
                for p, n, m in self.proxies:
                    if n.match(line["nick"]):
                        mt = m.match(text)
                        if mt:
                            protocol = p
                            src = self._make_user(mt.group(1), p)
                            text = mt.group(2)
                        break
                alttext = re_ircfmt.sub('', text)
                self.bus.post(Message(
                    protocol, None, src, dest, text, media, mtime,
                    None, None, None, mtype, None if alttext == text else alttext
                ))
            time.sleep(.5)

    def send(self, response):
        # -> Message
        raise NotImplementedError

    def forward(self, msg, protocol):
        # -> Message
        raise NotImplementedError

    def longtext(self, text):
        pass

    def _make_user(self, nick, protocol='irc', realname=None, ident=None):
        # the ident is not used at present
        return User(None, protocol, 'user', None, nick, realname, None, nick.rstrip('_'))

    def exit(self):
        self.run = False
        self.ircconn.quit('SIGINT received.')
