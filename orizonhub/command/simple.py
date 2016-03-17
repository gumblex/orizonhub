#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import random
import unicodedata

from .support import cp

srandom = random.SystemRandom()
facescore = lambda x,y: 1/2*math.erfc((0.5*y-x)/(2**0.5*(0.5*y**0.5)))*100
facescore.__doc__ = (
    'Calculate the "White Face Index" '
    'using the number of white faces generated.'
)
fstable = [facescore(i, 100) for i in range(101)]
revface = lambda x: min((abs(x-v), k) for k,v in enumerate(fstable))[1]
revface.__doc__ = (
    'Calculate the number of white faces required '
    'for a given "White Face Index".'
)

def uniq(seq): # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

@cp.register_command('233')
def cmd_233(expr, msg=None):
    try:
        num = max(min(int(expr.split()[0]), 100), 1)
    except Exception:
        num = 1
    w = math.ceil(num ** .5)
    h, rem = divmod(num, w)
    txt = '\n'.join(''.join(srandom.choice('🌝🌚') for i in range(w)) for j in range(h))
    if rem:
        txt += '\n' + ''.join(srandom.choice('🌝🌚') for i in range(rem))
    wcount = txt.count('🌝')
    wfi = facescore(wcount, num)
    if num > 9:
        txt += '\n' + '(🌝%d/🌚%d' % (wcount, num - wcount)
        if num > 41:
            txt += ', 🌝%.2f%%' % wfi
        txt += ')'
    return Response(txt, {'white': wcount, 'black': num - wcount, 
                    'white_face_index': wfi}, msg)

@cp.register_command('do')
def cmd_do(expr, msg=None):
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
                     '请坐和放宽，滚回以前的版本\n这就是你的人生\n是的，你的人生')),
        ('mac', ('您的计算机\n变得太热\n因为丢失了一些\n系统软件\n'
                 '您的计算机\n不能进入睡眠\n因此\n它将关闭'))
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
        if len(expr) < 5:
            res = ', '.join(unicodedata.name(ch) for ch in expr)
            return res
        else:
            return 'Something happened.'

@cp.register_command('fig', enabled=False)
def cmd_fig(expr, msg=None):
    '''/fig <char> Make figure out of moon faces.'''
    if expr:
        runapptask('fig', (expr,), (chatid, replyid))
    else:
        return srandom.choice('🌝🌚')

@cp.register_command('start', protocol=('telegrambot',))
def cmd_start(expr, msg=None):
    if chatid != -CFG['groupid']:
        return 'This is Orz Digger. It can help you search the long and boring chat log of the ##Orz group.\nSend me /help for help.'

@cp.register_command('cancel', protocol=('telegrambot',))
def cmd_cancel(expr, msg=None):
    cp.bus.telegrambot.bot_api('sendMessage', chat_id=msg['chat']['id'], text='Cancelled.', reply_to_message_id=msg['message_id'], reply_markup='{"hide_keyboard": true}')

@cp.register_command('hello', enabled=False)
def cmd_hello(expr, msg=None):
    return 'Hello!'

@cp.register_command('help')
def cmd_help(expr, msg=None):
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
