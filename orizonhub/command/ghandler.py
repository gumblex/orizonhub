#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
General Handlers
aka. Blackgun Handler
'''

from .support import cp

@cp.register_handler('autoclose')
def ghd_autoclose(msg):
    ...

@cp.register_handler('blackgun')
def ghd_blackgun(msg):
    ...

@cp.register_handler('welcome', protocol=('telegrambot',))
def ghd_welcome(msg):
    user = msg.media and msg.media.get('new_chat_participant')
    if (cp.config.command_config.get('welcome') and user
        and msg.chat.pid == cp.bus.telegrambot.identity.pid):
        uname = user['first_name']
        if 'last_name' in user:
            uname += ' ' + user['last_name']
        return '欢迎 %s 加入本群！' % uname

@cp.register_handler('private')
def ghd_private(msg):
    ...

