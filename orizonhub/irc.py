#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import queue
import logging
from zlib import crc32

from .utils import smartname, LRUCache
from .model import Protocol, Message, User, UserType, Response
from .ext.libirc import IRCConnection

logger = logging.getLogger('irc')

re_ircfmt = re.compile('[\x02\x1D\x1F\x16\x0F]|\x03(?:\d+(?:,\d+)?)?')
re_ircaction = re.compile('^\x01ACTION (.*)\x01$')
re_ircforward = re.compile(r'^\[(.+?)\] (.*)$|^\*\* ([^ ]+) (.*) \*\*$')
re_mention = re.compile(r'^(.+?)([:,].+$|$)')

md2ircfmt = lambda s: s.replace('*', '\x02').replace('_', '\x1D')

tgentity_templates = {
    'irc': {
        'bold': '\x02%(t)s\x02',
        'italic': '\x1D%(t)s\x1D',
        'text_link': '\x1F%(t)s\x1F (%(url)s)',
        'text_mention': '\x1F%(t)s\x1F',
    },
    'markdown': {
        'bold': '**%(t)s**',
        'italic': '_%(t)s_',
        'code': '`%(t)s`',
        'pre': '```\n%(t)s\n```',
        'text_link': '[%(t)s](%(url)s)',
        'text_mention': '_%(t)s_',
    },
    'markdown2': {
        'url': '[%(t)s](%(t)s)',
        'email': '[%(t)s](mailto:%(t)s)',
        'bold': '**%(t)s**',
        'italic': '_%(t)s_',
        'code': '`%(t)s`',
        'pre': '```\n%(t)s\n```',
        'text_link': '[%(t)s](%(url)s)',
        'text_mention': '_%(t)s_',
    }
}

def tgentity_conv(m: Message, style='irc') -> str:
    u16txt = m.text.encode('utf-16le')
    entities = sorted((e['offset'], e['length'], e) for e in m.media['entities'])
    pos = 0
    out = ''
    for offset, length, entity in entities:
        if offset > pos:
            out += u16txt[pos*2:offset*2].decode('utf-16le')
        entity['t'] = u16txt[offset*2:(offset+length)*2].decode('utf-16le')
        out += tgentity_templates[style].get(entity['type'], '%(t)s') % entity
        pos = offset + length
    out += u16txt[pos*2:].decode('utf-16le')
    return out

class IRCProtocol(Protocol):
    def __init__(self, config, bus):
        self.config = config
        self.cfg = config.protocols.irc
        self.bus = bus
        self.ircconn = None
        self.run = True
        self.ready = False
        # self.rate: max interval
        self.rate = 1/2
        self.poll_rate = 0.2
        self.send_q = queue.PriorityQueue()
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
        #self.line_length = 510 - 10
        # assume self.cfg.channel is ascii
        #self.line_length -= len(self.cfg.channel)
        # for max compatibility
        self.line_length = 420
        self.nickcache = LRUCache(32)

    def checkircconn(self):
        if self.ircconn and self.ircconn.sock:
            return
        self.ready = False
        self.ircconn = IRCConnection()
        self.ircconn.connect((self.cfg.server, self.cfg.port), use_ssl=self.cfg.ssl)
        if self.cfg.get('password'):
            self.ircconn.setpass(self.cfg.password)
        self.ircconn.setnick(self.cfg.username)
        self.ircconn.setuser(self.cfg.username, self.cfg.username)
        self.ircconn.join(self.cfg.channel)
        logger.info('IRC connected.')

    def start_polling(self):
        last_sent = 0
        while self.run:
            self.checkircconn()
            try:
                line = self.ircconn.parse(block=False)
            except Exception:
                logger.exception('Failed to poll from IRC.')
                continue
            mtime = int(time.time())
            #logger.debug('IRC: %s', line)
            if not line:
                pass
            elif line["cmd"] == "JOIN" and line["nick"] == self.cfg.username:
                logger.info('I joined IRC channel: %s' % line['dest'])
                self.ready = True
            elif line["cmd"] == "PRIVMSG":
                # ignored users
                if self.cfg.ignored_user and re.match(self.cfg.ignored_user, line["nick"]):
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
                alttext = self.identify_mention(re_ircfmt.sub('', text))
                self.bus.post(Message(
                    None, protocol, None, src, dest, text, media, mtime,
                    None, None, None, mtype, None if alttext == text else alttext
                ))
            wait = self.rate - time.perf_counter() + last_sent
            if wait > self.poll_rate or not self.ready:
                time.sleep(self.poll_rate)
            else:
                try:
                    prio, args = self.send_q.get_nowait()
                    if wait > 0:
                        time.sleep(wait)
                    self.checkircconn()
                    self.ircconn.say(*args)
                    last_sent = time.perf_counter()
                except queue.Empty:
                    time.sleep(self.poll_rate)
                except Exception:
                    self.send_q.put((prio, args))
                    logger.exception('Failed to send to IRC.')

    def send(self, response: Response, protocol: str, forwarded: Message) -> Message:
        # sending to proxies is not supported
        if protocol != 'irc':
            return
        if (response.info or {}).get('type') == 'markdown':
            text = md2ircfmt(response.text)
        else:
            text = (response.info or {}).get('alttext') or response.text
        if response.reply.mtype == 'private':
            prefix = ''
        elif self.cfg.get('colored'):
            prefix = '\x0315%s\x03: ' % self.smartname(response.reply.src)
        else:
            prefix = self.smartname(response.reply.src) + ': '
        lines = self.longtext(text, prefix, command=True)
        self.say(lines[0], response.reply.chat, (0, time.time(), 1))
        return Message(
            None, 'irc', None, self.identity, response.reply.chat, text,
            None, int(time.time()), None, None, response.reply,
            response.reply.mtype, response.text
        )

    def forward(self, msg: Message, protocol: str) -> Message:
        # `protocol` is ignored
        if protocol != 'irc' or msg.protocol in self.proxies:
            return
        if self.cfg.get('colored'):
            prefix = '[%s] ' % self.colored_smartname(msg.src)
        else:
            prefix = '[%s] ' % self.smartname(msg.src)
        text = msg.alttext or (tgentity_conv(msg)
                if msg.media and 'entities' in msg.media else msg.text)
        alttext = msg.alttext or (tgentity_conv(msg, 'markdown')
                if msg.media and 'entities' in msg.media else msg.text)
        if msg.fwd_src or msg.reply:
            if msg.fwd_src:
                src = self.smartname(msg.fwd_src)
                prefix2 = 'Fwd '
                replytext = None
            else:
                src = self.smartname(msg.reply.src)
                prefix2 = ''
                replytext = msg.reply.text
            if msg.reply and msg.reply.src.protocol == 'telegram' and (
                'telegrambot' in self.bus and
                self.bus.telegrambot.identity.pid == msg.reply.src.pid
                or 'telegramcli' in self.bus and
                self.bus.telegramcli.identity.pid == msg.reply.src.pid
            ):
                rnmatch = re_ircforward.match(msg.reply.text)
                if rnmatch:
                    src = rnmatch.group(1) or src
                    replytext = rnmatch.group(2) or replytext
            if replytext and self.cfg.get('long_reply'):
                replytext = replytext.replace('\n', '').strip()
                if len(replytext) > 8:
                    replytext = replytext[:8] + '…'
                prefix2 = 'Re %s:「%s」' % (src, replytext)
            else:
                prefix2 += src + ': '
            if self.cfg.get('colored'):
                prefix2 = '\x0315%s\x03' % prefix2
        else:
            prefix2 = ''
        lines = self.longtext(text, prefix, prefix2, alttext,
                              msg.media and msg.media.get('action'))
        for k, l in enumerate(lines):
            self.say(l, priority=(1, msg.time, k))
        return Message(
            None, 'irc', None, self.identity, self.dest, '\n'.join(lines),
            msg.media, int(time.time()), None, None, msg.reply, msg.mtype,
            msg.alttext
        )

    def longtext(self, text, prefix, prefix2='', alttext=None, action=False, command=False):
        line_length = self.line_length
        alttext = alttext or text
        if action:
            line_length -= 9
        lines = list(self._line_wrap((prefix2 + text).splitlines(), prefix, line_length))
        url = None
        if len(lines) > 5 or command and len(lines) > 2:
            try:
                url = self.bus.pastebin.paste_text(alttext)
            except NotImplementedError:
                pass
            except Exception:
                logger.exception('Failed to paste the text')
            if url is None:
                if command:
                    lines = [lines[0] + ' […] ' + lines[-1]]
                else:
                    lines = lines[:3]
                    lines[-1] += ' […]'
            else:
                return [prefix + prefix2 + '<long text> ' + url]
        elif command:
            return [prefix + prefix2 + ' '.join(lines)]
        for k, l in enumerate(lines):
            lines[k] = prefix + l
        return lines

    def say(self, line, dest=None, priority=(0, 0, 1)):
        # priority = (type, time, line)
        self.send_q.put((priority, (dest or self.cfg.channel, line)))

    @staticmethod
    def _line_wrap(lines, prefix, max_length):
        '''
        Algorithm to wrap long lines in IRC to avoid truncating.
        `prefix` is inserted before each line, i.e. sender's name
        '''
        for l in lines:
            sendl = prefix + l
            while len(sendl.encode('utf-8')) > max_length:
                # max utf-8 byte length is 4
                for ch in range(max_length//4, len(sendl)):
                    if len(sendl[:ch].encode('utf-8')) > max_length:
                        break
                yield sendl[len(prefix):ch-1]
                l = sendl[ch-1:]
                sendl = prefix + l
            else:
                if l:
                    yield l

    @staticmethod
    def _make_user(nick, protocol='irc', realname=None, ident=None):
        # the ident is not used at present
        return User(None, protocol, UserType.user, None,
                    nick, realname, None, nick.rstrip('_`'))

    def colored_smartname(self, user, limit=20):
        palette = (2, 3, 4, 5, 6, 7, 10, 12, 13)
        color = (user.pid or crc32(user.username.encode('utf-8')) or user.id or 0) % len(palette)
        return '\x03%02d%s\x03' % (palette[color], self.smartname(user, limit))

    def smartname(self, user, limit=20):
        name = smartname(user, limit)
        if user.username:
            self.nickcache[name] = user.username
        return name

    def identify_mention(self, text):
        match = re_mention.match(text)
        if match:
            mention, text = match.groups()
            nick = self.nickcache.get(mention)
            if nick:
                return match.expand(r'@%s\2' % nick)
        return text

    def close(self):
        if self.run:
            self.run = False
            self.ircconn.quit('SIGINT received')
