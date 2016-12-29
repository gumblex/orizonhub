#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ..model import User
from ..utils import nt_from_dict
from .support import cp, logger

@cp.register_command('nick', mtype=('private', 'group'), dependency='sqlite', enabled=False)
def cmd_nick(expr, msg=None):
    '''/nick <name> Set your nickname on other platforms'''
    nick = expr.strip()
    if not nick:
        return 'Usage: ' + cmd_nick.__doc__
    user = msg.src._asdict()
    user['alias'] = nick
    cp.bus.sqlite.update_user(nt_from_dict(User, user))
    return 'Set your nickname to ' + nick

#@cp.register_command('t2i', mtype=('group',))
#def cmd_t2i(expr, msg=None):
    #global CFG
    #if msg:
        #if expr == 'off' or CFG.get('t2i'):
            #CFG['t2i'] = False
            #return 'Telegram to IRC forwarding disabled.'
        #elif expr == 'on' or not CFG.get('t2i'):
            #CFG['t2i'] = True
            #return 'Telegram to IRC forwarding enabled.'

#@cp.register_command('i2t', mtype=('group',))
#def cmd_i2t(expr, msg=None):
    #global CFG
    #if msg:
        #if expr == 'off' or CFG.get('i2t'):
            #CFG['i2t'] = False
            #return 'IRC to Telegram forwarding disabled.'
        #elif expr == 'on' or not CFG.get('i2t'):
            #CFG['i2t'] = True
            #return 'IRC to Telegram forwarding enabled.'
