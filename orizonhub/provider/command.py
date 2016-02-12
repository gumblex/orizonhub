#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .base import *
import re
import math
import random

srandom = random.SystemRandom()
facescore = lambda x,y: 1/2*math.erfc((0.5*y-x)/(2**0.5*(0.5*y**0.5)))*100
fstable = [facescore(i, 100) for i in range(101)]
revface = lambda x: min((abs(x-v), k) for k,v in enumerate(fstable))[1]

class CommandHandler:
    def __init__(self, host):
        self.host = host
        self.prefix = "/'"
        self.cmds = {k[4:]: getattr(self, k) for k in dir(self) if k.startswith('cmd_')}

    def onmsg(self, msg):
        text = msg.get('text')
        if not text:
            return NotImplemented
        spl = text.split(' ', 1)
        cmd = spl[0]
        if msg['text'][0] in self.prefix:
            fn = self.cmds.get(cmd[1:])
            if fn:
                return fn(msg, spl[1] if len(spl) > 1 else '')
            else:
                return NotImplemented
        else:
            fn = self.cmds.get('')
            if fn:
                return fn(msg, text)
            else:
                return NotImplemented

    # Commands

    def cmd_(self, msg, expr):
        return NotImplemented

    def cmd_getmsg(self, msg, expr):
        '''/m <message_id> [...] Get specified message(s) by ID(s).'''
        try:
            if not expr:
                # raise for reply processing
                raise ValueError
            mids = tuple(map(int, expr.split()))
        except Exception:
            if 'reply_to_message' in msg:
                return 'Message ID: %d' % msg['reply_to_message']['message_id']
            else:
                return 'Syntax error. Usage: ' + cmd_getmsg.__doc__
        if msg['protocal'] == 'tgbot':
            self.host.tgbot.forwardmulti(mids, msg['chat']['id'], msg['message_id'])
        else:
            self. forwardmulti(mids, chatid, replyid)

    def cmd_context(self, msg, expr):
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
        typing(chatid)
        forwardmulti_t(range(mid - limit, mid + limit + 1), chatid, replyid)

    def cmd_quote(self, msg, expr):
        '''/quote Send a today's random message.'''
        typing(chatid)
        sec = daystart()
        msg = conn.execute('SELECT id FROM messages WHERE date >= ? AND date < ? ORDER BY RANDOM() LIMIT 1', (sec, sec + 86400)).fetchone()
        if msg is None:
            msg = conn.execute('SELECT id FROM messages ORDER BY RANDOM() LIMIT 1').fetchone()
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

    def cmd_search(self, msg, expr):
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
        typing(chatid)
        if uid is None:
            keyword = ' '.join(expr)
            sqr = conn.execute("SELECT id, src, text, date FROM messages WHERE text LIKE ? ORDER BY date DESC LIMIT ? OFFSET ?", ('%' + keyword + '%', limit, offset)).fetchall()
        else:
            sqr = conn.execute("SELECT id, src, text, date FROM messages WHERE src = ? AND text LIKE ? ORDER BY date DESC LIMIT ? OFFSET ?", (uid, '%' + keyword + '%', limit, offset)).fetchall()
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

    def cmd_mention(self, msg, expr):
        '''/mention Show last mention of you.'''
        if msg['chat']['id'] != -CFG['groupid']:
            return "This command can't be used in this chat."
            return
        tinput = ''
        uid = msg['from']['id']
        user = db_getuser(uid)
        if user[0]:
            res = conn.execute("SELECT * FROM messages WHERE (text LIKE ? OR reply_id IN (SELECT id FROM messages WHERE src = ?)) AND src != ? ORDER BY date DESC LIMIT 1", ('%@' + user[0] + '%', uid, CFG['botid'])).fetchone()
            userat = '@' + user[0] + ' '
        else:
            res = conn.execute("SELECT * FROM messages WHERE reply_id IN (SELECT id FROM messages WHERE src = ?) AND src != ? ORDER BY date DESC LIMIT 1", (uid, CFG['botid'])).fetchone()
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

    def cmd_uinfo(self, msg, expr):
        '''/user|/uinfo [@username] [minutes=1440] Show information about <@username>.'''
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
            r = conn.execute('SELECT src FROM messages WHERE date > ?', (time.time() - minutes * 60,)).fetchall()
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

    def cmd_stat(self, msg, expr):
        '''/stat [minutes=1440] Show statistics.'''
        try:
            minutes = min(max(int(expr), 1), 3359733)
        except Exception:
            minutes = 1440
        r = conn.execute('SELECT src FROM messages WHERE date > ?', (time.time() - minutes * 60,)).fetchall()
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

    def cmd_digest(self, msg, expr):
        return 'Not implemented.'

    def cmd_calc(self, msg, expr):
        '''/calc <expr> Calculate <expr>.'''
        # Too many bugs
        if expr:
            runapptask('calc', (expr,), (chatid, replyid))
        else:
            return 'Syntax error. Usage: ' + cmd_calc.__doc__

    def cmd_py(self, msg, expr):
        '''/py <expr> Evaluate Python 2 expression <expr>.'''
        if expr:
            if len(expr) > 1000:
                return 'Expression too long.'
            else:
                runapptask('py', (expr,), (chatid, replyid))
        else:
            return 'Syntax error. Usage: ' + cmd_py.__doc__

    def cmd_bf(self, msg, expr):
        '''/bf <expr> [|<input>] Evaluate Brainf*ck expression <expr> (with <input>).'''
        if expr:
            expr = expr.split('|', 1)
            inpt = expr[1] if len(expr) > 1 else ''
            runapptask('bf', (expr[0], inpt), (chatid, replyid))
        else:
            return 'Syntax error. Usage: ' + cmd_bf.__doc__

    def cmd_lisp(self, msg, expr):
        '''/lisp <expr> Evaluate Lisp(Scheme)-like expression <expr>.'''
        if expr:
            runapptask('lisp', (expr,), (chatid, replyid))
        else:
            return 'Syntax error. Usage: ' + cmd_lisp.__doc__

    def cmd_name(self, msg, expr):
        '''/name [pinyin] Get a Chinese name.'''
        runapptask('name', (expr,), (chatid, replyid))

    def cmd_cc(self, msg, expr):
        '''/cc <Chinese> Simplified-Traditional Chinese conversion.'''
        tinput = ''
        if 'reply_to_message' in msg:
            tinput = msg['reply_to_message'].get('text', '')
        tinput = (expr or tinput).strip()
        runapptask('cc', (tinput,), (chatid, replyid))

    def cmd_ime(self, msg, expr):
        '''/ime [pinyin] Simple Pinyin IME.'''
        tinput = ''
        if 'reply_to_message' in msg:
            tinput = msg['reply_to_message'].get('text', '')
        tinput = (expr or tinput).strip()
        if len(tinput) > 200:
            tinput = tinput[:200] + '…'
        if not tinput:
            return 'Syntax error. Usage: ' + cmd_ime.__doc__
            return
        runapptask('ime', (tinput,), (chatid, replyid))

    def cmd_cut(self, msg, expr):
        '''/cut [c|m] <something> Segment <something>.'''
        if expr[:2].strip() == 'c':
            lang = 'c'
            expr = expr[2:]
        elif expr[:2].strip() == 'm':
            lang = 'm'
            expr = expr[2:]
        else:
            lang = None
        tinput = ''
        if 'reply_to_message' in msg:
            tinput = msg['reply_to_message'].get('text', '')
        tinput = (expr or tinput).strip()
        if len(tinput) > 1000:
            tinput = tinput[:1000] + '……'
        if not tinput:
            return 'Syntax error. Usage: ' + cmd_cut.__doc__
            return
        runapptask('cut', (tinput, lang), (chatid, replyid))

    def cmd_wyw(self, msg, expr):
        '''/wyw [c|m] <something> Translate something to or from classical Chinese.'''
        if expr[:2].strip() == 'c':
            lang = 'c2m'
            expr = expr[2:]
        elif expr[:2].strip() == 'm':
            lang = 'm2c'
            expr = expr[2:]
        else:
            lang = None
        tinput = ''
        if 'reply_to_message' in msg:
            tinput = msg['reply_to_message'].get('text', '')
        tinput = (expr or tinput).strip()
        if len(tinput) > 1000:
            tinput = tinput[:1000] + '……'
        if not tinput:
            return 'Syntax error. Usage: ' + cmd_wyw.__doc__
            return
        typing(chatid)
        runapptask('wyw', (tinput, lang), (chatid, replyid))

    def cmd_say(self, msg, expr):
        '''/say Say something interesting.'''
        #typing(chatid)
        if expr:
            runapptask('reply', (expr,), (chatid, replyid))
        else:
            runapptask('say', (), (chatid, replyid))

    def cmd_reply(self, msg, expr):
        '''/reply [question] Reply to the conversation.'''
        if 'forward_from' in msg and msg['chat']['id'] < 0:
            return
        typing(chatid)
        text = ''
        if 'reply_to_message' in msg:
            text = msg['reply_to_message'].get('text', '')
        text = (expr.strip() or text or ' '.join(t[0] for t in conn.execute("SELECT text FROM messages ORDER BY date DESC LIMIT 2").fetchall())).replace('\n', ' ')
        runapptask('reply', (text,), (chatid, replyid))

    def cmd_cont(self, msg, expr):
        '''/cont [sentence] Complete the sentence.'''
        if 'forward_from' in msg and msg['chat']['id'] < 0:
            return
        typing(chatid)
        text = ''
        if 'reply_to_message' in msg:
            text = msg['reply_to_message'].get('text', '')
        text = (expr.strip() or text or conn.execute("SELECT text FROM messages ORDER BY date DESC LIMIT 1").fetchone()[0]).replace('\n', ' ')
        runapptask('cont', (text,), (chatid, replyid))

    def cmd_echo(self, msg, expr):
        '''/echo Parrot back.'''
        if 'ping' in expr.lower():
            return 'pong'
        elif expr:
            return expr
        else:
            return 'ping'

    def cmd_do(self, msg, expr):
        actions = collections.OrderedDict((
            ('shrug', '¯\\_(ツ)_/¯'),
            ('lenny', '( ͡° ͜ʖ ͡°)'),
            ('flip', '（╯°□°）╯︵ ┻━┻'),
            ('homo', '┌（┌　＾o＾）┐'),
            ('look', 'ಠ_ಠ'),
            ('cn', '[citation needed]'),
            ('boom', '💥'),
            ('tweet', '🐦'),
            ('blink', '👀'),
            ('see-no-evil', '🙈'),
            ('hear-no-evil', '🙉'),
            ('speak-no-evil', '🙊'),
            ('however', ('不要怪我们没有警告过你\n我们都有不顺利的时候\n'
                         'Something happened\n这真是让人尴尬\n'
                         '请坐和放宽，滚回以前的版本\n这就是你的人生\n是的，你的人生'))
        ))
        expr = expr.lower()
        res = actions.get(expr)
        if res:
            return res
        elif expr == 'help':
            return ', '.join(actions.keys())
        else:
            try:
                res = unicodedata.lookup(expr)
                return res
                return
            except KeyError:
                pass
            if len(expr) == 1:
                res = unicodedata.name(expr)
                return res
            else:
                return 'Something happened.'

    def cmd_t2i(self, msg, expr):
        global CFG
        if msg['chat']['id'] == -CFG['groupid']:
            if expr == 'off' or CFG.get('t2i'):
                CFG['t2i'] = False
                return 'Telegram to IRC forwarding disabled.'
            elif expr == 'on' or not CFG.get('t2i'):
                CFG['t2i'] = True
                return 'Telegram to IRC forwarding enabled.'

    def cmd_i2t(self, msg, expr):
        global CFG
        if msg['chat']['id'] == -CFG['groupid']:
            if expr == 'off' or CFG.get('i2t'):
                CFG['i2t'] = False
                return 'IRC to Telegram forwarding disabled.'
            elif expr == 'on' or not CFG.get('i2t'):
                CFG['i2t'] = True
                return 'IRC to Telegram forwarding enabled.'

    def cmd_autoclose(self, msg, expr):
        global CFG
        if msg['chat']['id'] == -CFG['groupid']:
            if CFG.get('autoclose'):
                CFG['autoclose'] = False
                return 'Auto closing brackets disabled.'
            else:
                CFG['autoclose'] = True
                return 'Auto closing brackets enabled.'

    def cmd__cmd(self, msg, expr):
        global SAY_P, APP_P
        if chatid < 0:
            return
        if expr == 'killserver':
            APP_P.terminate()
            APP_P = subprocess.Popen(APP_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            checkappproc()
            return 'Server restarted.'
            logging.info('Server restarted upon user request.')
        elif expr == 'commit':
            while 1:
                try:
                    logmsg(LOG_Q.get_nowait())
                except queue.Empty:
                    break
            db.commit()
            return 'DB committed.'
            logging.info('DB committed upon user request.')
        #elif expr == 'raiseex':  # For debug
            #async_func(_raise_ex)(Exception('/_cmd raiseex'))
        #else:
            #return 'ping'

    def cmd__welcome(self, msg, expr):
        if chatid > 0:
            return
        usr = msg["new_chat_participant"]
        USER_CACHE[usr["id"]] = (usr.get("username"), usr.get("first_name"), usr.get("last_name"))
        return '欢迎 %s 加入本群！' % dc_getufname(usr)

    facescore = lambda x,y: 1/2*math.erfc((0.5*y-x)/(2**0.5*(0.5*y**0.5)))*100

    fstable = [facescore(i, 100) for i in range(101)]
    revface = lambda x: min((abs(x-v), k) for k,v in enumerate(fstable))[1]

    def cmd_233(self, msg, expr):
        try:
            num = max(min(int(expr), 100), 1)
        except Exception:
            num = 1
        w = math.ceil(num ** .5)
        h, rem = divmod(num, w)
        txt = '\n'.join(''.join(srandom.choice('🌝🌚') for i in range(w)) for j in range(h))
        if rem:
            txt += '\n' + ''.join(srandom.choice('🌝🌚') for i in range(rem))
        wcount = txt.count('🌝')
        if num > 9:
            txt += '\n' + '(🌝%d/🌚%d' % (wcount, num - wcount)
            if num > 41:
                txt += ', 🌝%.2f%%' % facescore(wcount, num)
            txt += ')'
        return txt

    def cmd_fig(self, msg, expr):
        '''/fig <char> Make figure out of moon faces.'''
        if expr:
            runapptask('fig', (expr,), (chatid, replyid))
        else:
            return srandom.choice('🌝🌚')

    def cmd_start(self, msg, expr):
        if chatid != -CFG['groupid']:
            return 'This is Orz Digger. It can help you search the long and boring chat log of the ##Orz group.\nSend me /help for help.'











    def cmd_cancel(self, msg, expr):
        if msg['protocal'] != 'tgbot':
            return NotImplemented
        bot_api('sendMessage', chat_id=msg['chat']['id'], text='Cancelled.', reply_to_message_id=msg['message_id'], reply_markup='{"hide_keyboard": true}')

    def cmd_hello(self, msg, expr):
        return 'Hello!'

    def cmd_233(self, msg, expr, query=None):
        if query:
            num = query['num']
        else:
            try:
                num = max(min(int(expr), 100), 1)
            except Exception:
                num = 1
        w = math.ceil(num ** .5)
        h, rem = divmod(num, w)
        txt = '\n'.join(''.join(srandom.choice('🌝🌚') for i in range(w)) for j in range(h))
        if rem:
            txt += '\n' + ''.join(srandom.choice('🌝🌚') for i in range(rem))
        wcount = txt.count('🌝')
        if num > 9:
            txt += '\n' + '(🌝%d/🌚%d' % (wcount, num - wcount)
            if num > 41:
                txt += ', 🌝%.2f%%' % facescore(wcount, num)
            txt += ')'
        return txt

    def cmd_help(self, msg, expr):
        if msg['protocal'] != 'tgbot':
            return NotImplemented
        if expr:
            if expr in self.cmds:
                h = self.cmds[expr].__doc__
                if h:
                    return h
                else:
                    return 'Help is not available for ' + expr
            else:
                return 'Command not found.'
        elif chatid == -self.host.tgbot.cfg['groupid']:
            return 'Full help disabled in this group.'
        elif chatid > 0:
            return '\n'.join(uniq(cmd.__doc__ for cmdname, cmd in self.cmds.items() if cmd.__doc__ and self.check_protocal(cmdname, 'tgbot')))
        else:
            return '\n'.join(uniq(cmd.__doc__ for cmdname, cmd in self.cmds.items() if cmd.__doc__ and self.check_protocal(cmdname, 'tgbot') and not self.cmdinfo(cmdname).get('tgpriv')))
