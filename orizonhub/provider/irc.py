#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import logging

from ..utils import smartname
from ..model import Protocol, Message, User, UserType
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
        # self.rate: max interval
        self.rate = 1/2
        self.last_sent = 0
        self.identity = User(None, 'irc', UserType.user, None, self.cfg.username,
                             config.bot_fullname, None, config.bot_nickname)
        self.dest = User(None, 'irc', UserType.group, None, self.cfg.channel,
                         self.cfg.channel, None, config.group_name)
        self.proxies = {p: (re.compile(n), re.compile(m)) for p, n, m in self.cfg.proxies}
        # IRC messages are always lines of characters terminated with a CR-LF
        # (Carriage Return - Line Feed) pair, and these messages SHALL NOT
        # exceed 512 characters in length, counting all characters including
        # the trailing CR-LF. Thus, there are 510 characters maximum allowed
        # for the command and its parameters.
        # PRIVMSG %s :%s
        self.line_length = 510 - 10
        # assume self.cfg.channel is ascii
        self.line_length -= len(self.cfg.channel)

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
            #logging.debug('IRC: %s', line)
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
                    src = dest = self._make_user(line["nick"])
                elif line["dest"] == self.cfg.channel:
                    mtype = 'group'
                    src = self._make_user(line["nick"])
                    dest = self.dest
                else:
                    continue
                # should use /whois and cache to get realname?
                protocol = 'irc'
                action = re_ircaction.match(line["msg"])
                if action:
                    text = action.group(1).strip()
                    media = {'action': True}
                else:
                    text = line["msg"].strip()
                    media = None
                # OrzTox bot have actions and quotes
                for p, val in self.proxies.items():
                    n, m = val
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
            time.sleep(.2)

    def send(self, response, protocol):
        # -> Message
        # sending to proxies is not supported
        if protocol != 'irc':
            return
        lines = response.text.splitlines()
        text = smartname(response.reply.src) + ': '
        if len(lines) < 3:
            text += ' '.join(lines)
        else:
            text += lines[0] + ' […] ' + lines[-1]
        self.say(text, response.reply.chat)
        return Message(
            'irc', None, self.identity, response.reply.chat, text, None,
            int(time.time()), None, None, response.reply,
            response.reply.mtype, response.text
        )

    def forward(self, msg, protocol):
        # -> Message
        # `protocol` is ignored
        if protocol != 'irc' or msg.protocol in self.proxies:
            return
        if msg.fwd_src:
            text = 'Fwd %s: %s' % (smartname(msg.fwd_src), msg.text)
        elif msg.reply:
            text = '%s: %s' % (smartname(msg.reply.src), msg.text)
        else:
            text = msg.text
        lines = self.longtext(text, msg.media and msg.media.get('action'))
        for l in lines:
            self.say(l)
        return Message(
            'irc', None, self.identity, self.dest, '\n'.join(lines), msg.media,
            int(time.time()), None, None, msg.reply, msg.mtype, msg.alttext
        )

    def longtext(self, text, action=False):
        line_length = self.line_length
        if action:
            line_length -= 9
        lines = list(self._line_wrap(text.splitlines(), line_length))
        url = None
        if len(lines) > 3:
            try:
                url = self.bus.pastebin.paste_text(text)
            except NotImplementedError:
                pass
            except Exception:
                logging.exception('Failed to paste the text')
            if url is None:
                lines = lines[:3]
                lines[-1] += ' […]'
            else:
                lines = ['<long text> ' + url]
        return lines

    def say(self, line, dest=None):
        wait = self.rate - time.perf_counter() + self.last_sent
        if wait > 0:
            time.sleep(wait)
        self.ircconn.say(dest or self.cfg.channel, line)
        self.last_sent = time.perf_counter()

    @staticmethod
    def _line_wrap(lines, max_length):
        for l in lines:
            while len(l.encode('utf-8')) > max_length:
                # max utf-8 byte length is 4
                for ch in range(max_length//4, len(l)):
                    if len(l[:ch].encode('utf-8')) > max_length:
                        break
                yield l[:ch-1]
                l = l[ch-1:]
            else:
                if l:
                    yield l

    @staticmethod
    def _make_user(nick, protocol='irc', realname=None, ident=None):
        # the ident is not used at present
        return User(None, protocol, UserType.user, None,
                    nick, realname, None, nick.rstrip('_'))

    def close(self):
        if self.run:
            self.run = False
            self.ircconn.quit('SIGINT received')
