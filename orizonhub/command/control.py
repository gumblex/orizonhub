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

@cp.register_command('t2i', protocol=('telegrambot', 'irc'), mtype=('group',))
def cmd_t2i(expr, msg=None):
    if msg:
        if expr == 'off' or cp.bus.irc.forward_enabled:
            cp.bus.irc.forward_enabled = False
            return 'Forwarding to IRC disabled.'
        elif expr == 'on' or not cp.bus.irc.forward_enabled:
            cp.bus.irc.forward_enabled = True
            return 'Forwarding to IRC enabled.'

@cp.register_command('i2t', protocol=('telegrambot', 'irc'), mtype=('group',))
def cmd_i2t(expr, msg=None):
    if msg:
        if expr == 'off' or cp.bus.telegrambot.forward_enabled:
            cp.bus.telegrambot.forward_enabled = False
            return 'Forwarding to Telegram disabled.'
        elif expr == 'on' or not cp.bus.telegrambot.forward_enabled:
            cp.bus.telegrambot.forward_enabled = True
            return 'Forwarding to Telegram enabled.'
