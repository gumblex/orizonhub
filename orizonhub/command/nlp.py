#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .support import cp

@cp.register_command('name')
def cmd_name(expr, msg=None):
    '''/name [pinyin] Get a Chinese name.'''
    cp.external('name', expr)

@cp.register_command('cc')
def cmd_cc(expr, msg=None):
    '''/cc <Chinese> Simplified-Traditional Chinese conversion.'''
    tinput = ''
    if 'reply_to_message' in msg:
        tinput = msg['reply_to_message'].get('text', '')
    tinput = (expr or tinput).strip()
    cp.external('cc', tinput)

@cp.register_command('ime')
def cmd_ime(expr, msg=None):
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
    cp.external('ime', tinput)

@cp.register_command('cut')
def cmd_cut(expr, msg=None):
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
    cp.external('cut', tinput, lang)

@cp.register_command('wyw')
def cmd_wyw(expr, msg=None):
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
    cp.bus.status(msg.chat, 'typing')
    cp.external('wyw', tinput, lang)

@cp.register_command('say')
def cmd_say(expr, msg=None):
    '''/say Say something interesting.'''
    #cp.bus.status(msg.chat, 'typing')
    if expr:
        cp.external('reply', expr)
    else:
        cp.external('say')

@cp.register_command('reply')
def cmd_reply(expr, msg=None):
    '''/reply [question] Reply to the conversation.'''
    if 'forward_from' in msg and msg['chat']['id'] < 0:
        return
    cp.bus.status(msg.chat, 'typing')
    text = ''
    if 'reply_to_message' in msg:
        text = msg['reply_to_message'].get('text', '')
    text = (expr.strip() or text or ' '.join(t[0] for t in cp.bus.sqlite.select("SELECT text FROM messages ORDER BY date DESC LIMIT 2").fetchall())).replace('\n', ' ')
    cp.external('reply', text)

