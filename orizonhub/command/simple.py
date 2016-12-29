#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import random
import collections
import unicodedata

from .support import cp, Response

def uniq(seq): # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

@cp.register_command('start', protocol=('telegrambot',), mtype=('private',))
def cmd_start(expr, msg=None):
    return 'This is %s.\nSend me /help for help.' % cp.config.bot_nickname

@cp.register_command('help')
def cmd_help(expr, msg=None):
    '''/help [command] List available commands or show help for some command.'''
    # TODO
    if expr:
        if expr in cp.commands:
            h = cp.commands[expr].usage
            if h:
                return h
            else:
                return 'Help is not available for ' + expr
        else:
            return 'Command not found.'
    elif msg.mtype == 'private' and msg.protocol != 'irc':
        return '\n'.join(uniq(cmd.usage for cmdname, cmd in cp.commands.items() if
                cmd.usage and not (
                cmd.protocol and msg.protocol not in cmd.protocol
                or cmd.mtype and msg.mtype not in cmd.mtype
                or cmd.dependency and cmd.dependency not in cp.bus.handler.providers)))
    else:
        return 'Commands: %s. For usage: /help [cmd]' % ', '.join(uniq(
            '/' + cmdname for cmdname, cmd in cp.commands.items() if not (
                cmd.protocol and msg.protocol not in cmd.protocol
                or cmd.mtype and msg.mtype not in cmd.mtype
                or cmd.dependency and cmd.dependency not in cp.bus.handler.providers)
        ))
