#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
General Handlers
'''

from .support import cp

@cp.register_handler('welcome', protocol=('telegrambot',), mtype=('group',))
def ghd_tg_welcome(msg):
    '''
    Send a welcome message when a new member comes in the Telegram group.
    '''
    user = msg.media and msg.media.get('new_chat_participant')
    if (cp.config.command_config.get('welcome') and user
        and msg.chat.pid == cp.bus.telegrambot.identity.pid):
        uname = user['first_name']
        if 'last_name' in user:
            uname += ' ' + user['last_name']
        return '欢迎 %s 加入本群！' % uname
