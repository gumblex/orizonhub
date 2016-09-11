#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import datetime
import functools
import collections

from ..utils import smartname
from .support import cp, Message, Response

re_search_number = re.compile(r'([0-9]+)(,[0-9]+)?')

formattime = lambda timestamp: datetime.datetime.fromtimestamp(
    timestamp, cp.bus.timezone).strftime('%Y-%m-%d %H:%M')

daystart = lambda sec=None: cp.bus.timezone.normalize(datetime.datetime.combine(
            datetime.datetime.fromtimestamp(sec or time.time(), cp.bus.timezone),
            datetime.time(tzinfo=cp.bus.timezone))).timestamp()

def ellipsisresult(s, find, maxctx=50):
    if find:
        try:
            lnid = s.lower().index(find.lower())
            r = s[max(0, lnid - maxctx):min(len(s), lnid + maxctx)].strip()
            if len(r) < len(s):
                r = '… %s …' % r
            return r
        except ValueError:
            return s
    else:
        return s

@cp.register_command('m', mtype=('private', 'group'), dependency='sqlite')
def cmd_getmsg(expr, msg=None):
    '''/m <message_id> [...] Get specified message(s) by ID(s).'''
    try:
        if not expr:
            # raise for reply processing
            raise ValueError
        mids = tuple(map(int, expr.split()))
    except Exception:
        # FIXME: msg.reply won't have a id
        if msg.reply and msg.reply.id:
            return 'Message ID: %d' % msg.reply.id
        else:
            return 'Syntax error. Usage: ' + cmd_getmsg.__doc__
    messages = list(filter(None, (cp.bus.sqlite.getmsg(mid) for mid in mids)))
    if len(messages) == 1:
        return forward_tgbot(msg, messages[0])
    else:
        return Response(forwardmulti_text(messages),
                        {'type': 'forward', 'messages': messages}, msg, None)

@cp.register_command('context', mtype=('private', 'group'), dependency='sqlite')
def cmd_context(expr, msg=None):
    '''/context <message_id> [number=2] Show the specified message and its context. max=10'''
    expr = expr.split(' ')
    try:
        if len(expr) > 1:
            mid = max(int(expr[0]), 1)
            limit = max(min(int(expr[1]), 10), 1)
        else:
            mid, limit = int(expr[0]), 2
    except Exception:
        return 'Syntax error. Usage: ' + cmd_context.__doc__
    messages = list(filter(None, (cp.bus.sqlite.getmsg(mid) for mid in range(mid - limit, mid + limit + 1))))
    return Response(forwardmulti_text(messages),
            {'type': 'forward', 'messages': messages}, msg, None)

@cp.register_command('quote', mtype=('private', 'group'), dependency='sqlite')
def cmd_quote(expr, msg=None):
    '''/quote Send a today's random message.'''
    #cp.bus.status(msg.chat, 'typing')
    sec = daystart()
    mid = cp.bus.sqlite.select('SELECT id FROM messages WHERE time >= ? AND time < ? ORDER BY RANDOM() LIMIT 1', (sec, sec + 86400)).fetchone()
    if mid is None:
        mid = cp.bus.sqlite.select('SELECT id FROM messages ORDER BY RANDOM() LIMIT 1').fetchone()
    fwd = cp.bus.sqlite.getmsg(mid[0])
    return forward_tgbot(msg, fwd)

@cp.register_command('search', mtype=('private', 'group'), dependency='sqlite')
@cp.register_command('s', mtype=('private', 'group'), dependency='sqlite')
def cmd_search(expr, msg=None):
    '''/search|/s [@username] [keyword] [number=5|number,offset] Search the group log for recent messages. max(number)=20'''
    username, uid, limit, offset = None, None, 5, 0
    if expr:
        expr = expr.split(' ')
        if len(expr) > 1:
            ma = re_search_number.match(expr[-1])
            if ma:
                expr = expr[:-1]
                limit = max(min(int(ma.group(1)), 20), 1)
                offset = int(ma.group(2)[1:]) if ma.group(2) else 0
        if expr[0][0] == '@':
            username = expr[0][1:]
            keyword = ' '.join(expr[1:])
        else:
            keyword = ' '.join(expr)
    else:
        keyword = ''
    if username:
        uid = db_getuidbyname(username)
    if uid is None:
        keyword = ' '.join(expr)
        sqr = cp.bus.sqlite.select("SELECT id, src, text, time FROM messages WHERE text LIKE ? ORDER BY time DESC LIMIT ? OFFSET ?", ('%' + keyword + '%', limit, offset)).fetchall()
    else:
        sqr = cp.bus.sqlite.select("SELECT id, src, text, time FROM messages WHERE src = ? AND text LIKE ? ORDER BY time DESC LIMIT ? OFFSET ?", (uid, '%' + keyword + '%', limit, offset)).fetchall()
    result = []
    for mid, fr, text, mtime in sqr:
        text = ellipsisresult(text, keyword)
        if len(text) > 100:
            text = text[:100] + '…'
        if uid:
            result.append('[%d|%s] %s' % (mid, formattime(mtime), text))
        else:
            result.append('[%d|%s] %s: %s' % (mid, formattime(mtime), smartname(cp.bus.sqlite.getuser(fr)), text))
    return '\n'.join(result) or 'Found nothing.'

@cp.register_command('mention', protocol=('telegrambot',), mtype=('group',), dependency='sqlite')
def cmd_mention(expr, msg=None):
    '''/mention [offset] Show last mention of you.'''
    if not msg:
        return "This command can't be used in this chat."
    offset = ''
    if expr:
        try:
            offset = ' OFFSET %d' % int(msg.strip())
        except ValueError:
            pass
    user = msg.src
    if user.username:
        res = cp.bus.sqlite.select("SELECT id, protocol, pid FROM messages WHERE (text LIKE ? OR reply_id IN (SELECT id FROM messages WHERE src = ?)) AND src != ? ORDER BY time DESC LIMIT 1" + offset, ('%@' + user.username + '%', user.id, cp.bus.telegrambot.identity.id)).fetchone()
        userat = '@' + user.username + ' '
    else:
        res = cp.bus.sqlite.select("SELECT id, protocol, pid FROM messages WHERE reply_id IN (SELECT id FROM messages WHERE src = ?) AND src != ? ORDER BY time DESC LIMIT 1" + offset, (user.id, cp.bus.telegrambot.identity.id)).fetchone()
        userat = ''
    if res:
        msgid, msgproto, msgpid = res
        referred = cp.bus.sqlite.getmsg(msgid)
        if msgproto.startswith('telegram'):
            text = userat + 'You were mentioned in this message.'
            try:
                m = cp.bus.telegrambot.bot_api('sendMessage', chat_id=msg.chat.pid,
                    text=text, reply_to_message_id=msgpid)
                return Response(text, {'type': 'forward', 'messages': (referred,)},
                    msg, (cp.bus.telegrambot._make_message(m),))
            except cp.bus.telegrambot.BotAPIFailed:
                return forward_tgbot(msg, referred)
        else:
            return forward_tgbot(msg, referred)
    else:
        return 'No mention found.'

def timestring(minutes):
    h, m = divmod(minutes, 60)
    d, h = divmod(h, 24)
    return (' %d 天' % d if d else '') + (' %d 小时' % h if h else '') + (' %d 分钟' % m if m else '')

@cp.register_command('user', dependency='sqlite')
def cmd_uinfo(expr, msg=None):
    '''/user [@username] [minutes=1440] Show information about <@username>.'''
    if msg.reply:
        user = msg.reply.src
    else:
        user = None
    if expr:
        expr = expr.split(' ')
        username = expr[0]
        if not username.startswith('@'):
            user = user or msg.src
            try:
                minutes = min(max(int(expr[0]), 1), 3359733)
            except Exception:
                minutes = 1440
        else:
            uid = db_getuidbyname(username[1:])
            if not uid:
                return 'User not found.'
            user = cp.bus.sqlite.getuser(uid)
            try:
                minutes = min(max(int(expr[1]), 1), 3359733)
            except Exception:
                minutes = 1440
    else:
        user = user or msg.src
        minutes = 1440
    uinfoln = []
    if user.username:
        uinfoln.append('@' + user.username)
    uinfoln.append(smartname(user))
    if user.pid:
        uinfoln.append('ID: %s' % user.pid)
    result = [', '.join(uinfoln)]
    if msg.mtype == 'group':
        r = cp.bus.sqlite.select('SELECT src FROM messages WHERE date > ?', (time.time() - minutes * 60,)).fetchall()
        timestr = timestring(minutes)
        if r:
            ctr = collections.Counter(i[0] for i in r)
            if user.id in ctr:
                rank = sorted(ctr, key=ctr.__getitem__, reverse=True).index(user.id) + 1
                result.append('在最近%s内发了 %s 条消息，占 %.2f%%，位列第 %s。' % (timestr, ctr[user.id], ctr[user.id]/len(r)*100, rank))
            else:
                result.append('在最近%s内没发消息。' % timestr)
        else:
            result.append('在最近%s内没发消息。' % timestr)
    return '\n'.join(result)

@cp.register_command('stat', mtype=('private', 'group'), dependency='sqlite')
def cmd_stat(expr, msg=None):
    '''/stat [minutes=1440] Show statistics.'''
    try:
        minutes = min(max(int(expr), 1), 3359733)
    except Exception:
        minutes = 1440
    r = cp.bus.sqlite.select('SELECT src FROM messages WHERE time > ?', (time.time() - minutes * 60,)).fetchall()
    timestr = timestring(minutes)
    if not r:
        return '在最近%s内无消息。' % timestr
    ctr = collections.Counter(i[0] for i in r)
    mcomm = ctr.most_common(5)
    count = len(r)
    msg = ['在最近%s内有 %s 条消息，平均每分钟 %.2f 条。' % (timestr, count, count/minutes)]
    msg.extend('%s: %s 条，%.2f%%' % (smartname(cp.bus.sqlite.getuser(k)), v, v/count*100) for k, v in mcomm)
    msg.append('其他用户 %s 条，人均 %.2f 条' % (count - sum(v for k, v in mcomm), count / len(ctr)))
    return '\n'.join(msg)

@cp.register_command('digest', mtype=('private', 'group'), enabled=False)
def cmd_digest(expr, msg=None):
    return 'https://daily.orz.chat'

@functools.lru_cache(maxsize=10)
def db_getuidbyname(username):
    if username.startswith('#'):
        try:
            pid = int(username[1:])
        except ValueError:
            return None
        uid = cp.bus.sqlite.select('SELECT id FROM users WHERE pid = ?', (pid,)).fetchone()
        if uid:
            return uid[0]
    else:
        uid = cp.bus.sqlite.select('SELECT id FROM users WHERE username LIKE ?', (username,)).fetchone()
        if uid:
            return uid[0]

def forward_tgbot(origmsg: Message, fwd: Message) -> Response:
    if origmsg.protocol == 'telegrambot' and fwd.protocol.startswith('telegram'):
        try:
            m = cp.bus.telegrambot.bot_api('forwardMessage', chat_id=origmsg.chat.pid,
                from_chat_id=fwd.chat.pid, message_id=fwd.pid)
            return Response(forwardmulti_text((fwd,)),
                {'type': 'forward', 'messages': (fwd,)}, origmsg,
                (cp.bus.telegrambot._make_message(m),))
        except cp.bus.telegrambot.BotAPIFailed:
            return Response(forwardmulti_text((fwd,)),
                {'type': 'forward', 'messages': (fwd,)}, origmsg, None)
    else:
        return Response(forwardmulti_text((fwd,)),
            {'type': 'forward', 'messages': (fwd,)}, origmsg, None)

def forwardmulti_text(messages):
    text = []
    for m in messages:
        text.append('[%s] %s: %s' % (formattime(m.time), smartname(m.src), m.text))
    return '\n'.join(text) or 'Message%s not found.' % ('s' if len(messages) != 1 else '')
