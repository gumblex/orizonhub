#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from .support import cp, Response

@cp.register_command('m', dependency='sqlite')
def cmd_getmsg(expr, msg=None):
    '''/m <message_id> [...] Get specified message(s) by ID(s).'''
    try:
        if not expr:
            # raise for reply processing
            raise ValueError
        mids = tuple(map(int, expr.split()))
    except Exception:
        if 'reply_to_message' in msg:
            return 'Message ID: t%d' % msg['reply_to_message']['message_id']
        else:
            return 'Syntax error. Usage: ' + cmd_getmsg.__doc__
    if msg['protocal'] == 'tgbot':
        self.host.tgbot.forwardmulti(mids, msg['chat']['id'], msg['message_id'])
    else:
        self.forwardmulti(mids, chatid, replyid)

@cp.register_command('context', dependency='sqlite')
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
        return
    #cp.bus.status(msg.chat, 'typing')
    forwardmulti_t(range(mid - limit, mid + limit + 1), chatid, replyid)

@cp.register_command('quote', dependency='sqlite')
def cmd_quote(expr, msg=None):
    '''/quote Send a today's random message.'''
    #cp.bus.status(msg.chat, 'typing')
    sec = daystart()
    msg = cp.bus.sqlite.select('SELECT id FROM messages WHERE date >= ? AND date < ? ORDER BY RANDOM() LIMIT 1', (sec, sec + 86400)).fetchone()
    if msg is None:
        msg = cp.bus.sqlite.select('SELECT id FROM messages ORDER BY RANDOM() LIMIT 1').fetchone()
    #forwardmulti((msg[0]-1, msg[0], msg[0]+1), chatid, replyid)
    forward(msg[0], chatid, replyid)

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

re_search_number = re.compile(r'([0-9]+)(,[0-9]+)?')

@cp.register_command('search', dependency='sqlite')
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
        sqr = cp.bus.sqlite.select("SELECT id, src, text, date FROM messages WHERE text LIKE ? ORDER BY date DESC LIMIT ? OFFSET ?", ('%' + keyword + '%', limit, offset)).fetchall()
    else:
        sqr = cp.bus.sqlite.select("SELECT id, src, text, date FROM messages WHERE src = ? AND text LIKE ? ORDER BY date DESC LIMIT ? OFFSET ?", (uid, '%' + keyword + '%', limit, offset)).fetchall()
    result = []
    for mid, fr, text, date in sqr:
        text = ellipsisresult(text, keyword)
        if len(text) > 100:
            text = text[:100] + '…'
        if uid:
            result.append('[%d|%s] %s' % (mid, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(date + CFG['timezone'] * 3600)), text))
        else:
            result.append('[%d|%s] %s: %s' % (mid, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(date + CFG['timezone'] * 3600)), db_getufname(fr), text))
    return '\n'.join(result) or 'Found nothing.'

@cp.register_command('mention', protocol=('telegrambot',), dependency='sqlite')
def cmd_mention(expr, msg=None):
    '''/mention Show last mention of you.'''
    if msg['chat']['id'] != -CFG['groupid']:
        return "This command can't be used in this chat."
        return
    tinput = ''
    uid = msg['from']['id']
    user = db_getuser(uid)
    if user[0]:
        res = cp.bus.sqlite.select("SELECT * FROM messages WHERE (text LIKE ? OR reply_id IN (SELECT id FROM messages WHERE src = ?)) AND src != ? ORDER BY date DESC LIMIT 1", ('%@' + user[0] + '%', uid, CFG['botid'])).fetchone()
        userat = '@' + user[0] + ' '
    else:
        res = cp.bus.sqlite.select("SELECT * FROM messages WHERE reply_id IN (SELECT id FROM messages WHERE src = ?) AND src != ? ORDER BY date DESC LIMIT 1", (uid, CFG['botid'])).fetchone()
        userat = ''
    if res:
        reid = res[0]
        if reid > 0:
            sendmsg(userat + 'You were mentioned in this message.', chatid, reid)
        else:
            forward(reid, chatid, replyid)
    else:
        return 'No mention found.'

def timestring(minutes):
    h, m = divmod(minutes, 60)
    d, h = divmod(h, 24)
    return (' %d 天' % d if d else '') + (' %d 小时' % h if h else '') + (' %d 分钟' % m if m else '')

@cp.register_command('user', dependency='sqlite')
def cmd_uinfo(expr, msg=None):
    '''/user [@username] [minutes=1440] Show information about <@username>.'''
    tinput = ''
    if 'reply_to_message' in msg:
        uid = msg['reply_to_message']['from']['id']
    else:
        uid = None
    if expr:
        expr = expr.split(' ')
        username = expr[0]
        if not username.startswith('@'):
            uid = uid or msg['from']['id']
            try:
                minutes = min(max(int(expr[0]), 1), 3359733)
            except Exception:
                minutes = 1440
        else:
            uid = db_getuidbyname(username[1:])
            if not uid:
                return 'User not found.'
                return
            try:
                minutes = min(max(int(expr[1]), 1), 3359733)
            except Exception:
                minutes = 1440
    else:
        uid = uid or msg['from']['id']
        minutes = 1440
    user = db_getuser(uid)
    uinfoln = []
    if user[0]:
        uinfoln.append('@' + user[0])
    uinfoln.append(db_getufname(uid))
    uinfoln.append('ID: %s' % uid)
    result = [', '.join(uinfoln)]
    if msg['chat']['id'] == -CFG['groupid']:
        r = cp.bus.sqlite.select('SELECT src FROM messages WHERE date > ?', (time.time() - minutes * 60,)).fetchall()
        timestr = timestring(minutes)
        if r:
            ctr = collections.Counter(i[0] for i in r)
            if uid in ctr:
                rank = sorted(ctr, key=ctr.__getitem__, reverse=True).index(uid) + 1
                result.append('在最近%s内发了 %s 条消息，占 %.2f%%，位列第 %s。' % (timestr, ctr[uid], ctr[uid]/len(r)*100, rank))
            else:
                result.append('在最近%s内没发消息。' % timestr)
        else:
            result.append('在最近%s内没发消息。' % timestr)
    return '\n'.join(result)

@cp.register_command('stat', dependency='sqlite')
def cmd_stat(expr, msg=None):
    '''/stat [minutes=1440] Show statistics.'''
    try:
        minutes = min(max(int(expr), 1), 3359733)
    except Exception:
        minutes = 1440
    r = cp.bus.sqlite.select('SELECT src FROM messages WHERE date > ?', (time.time() - minutes * 60,)).fetchall()
    timestr = timestring(minutes)
    if not r:
        return '在最近%s内无消息。' % timestr
        return
    ctr = collections.Counter(i[0] for i in r)
    mcomm = ctr.most_common(5)
    count = len(r)
    msg = ['在最近%s内有 %s 条消息，平均每分钟 %.2f 条。' % (timestr, count, count/minutes)]
    msg.extend('%s: %s 条，%.2f%%' % (db_getufname(k), v, v/count*100) for k, v in mcomm)
    msg.append('其他用户 %s 条，人均 %.2f 条' % (count - sum(v for k, v in mcomm), count / len(ctr)))
    return '\n'.join(msg)

@cp.register_command('digest', enabled=False)
def cmd_digest(expr, msg=None):
    return 'Not implemented.'

