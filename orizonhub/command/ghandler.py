#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
General Handlers
'''

from .support import cp

@cp.register_handler('private', mtype=('private',))
def ghd_private(msg):
    '''
    Handler for private non-command messages. (eg. /reply)
    '''
    if msg and 'reply' in cp.commands:
        return cp.reply.func(msg.text, msg)

@cp.register_handler('autoclose', mtype=('group',))
def ghd_autoclose(msg):
    '''
    Auto close brackets in users' messages.
    '''
    if (not msg or not cp.config.command_config.get('autoclose')):
        return
    openbrckt = ('([{（［｛⦅〚⦃“‘‹«「〈《【〔⦗『〖〘｢⟦⟨⟪⟮⟬⌈⌊⦇⦉❛❝❨❪❴❬❮❰❲'
                 '⏜⎴⏞〝︵⏠﹁﹃︹︻︗︿︽﹇︷〈⦑⧼﹙﹛﹝⁽₍⦋⦍⦏⁅⸢⸤⟅⦓⦕⸦⸨｟⧘⧚⸜⸌⸂⸄⸉᚛༺༼')
    clozbrckt = (')]}）］｝⦆〛⦄”’›»」〉》】〕⦘』〗〙｣⟧⟩⟫⟯⟭⌉⌋⦈⦊❜❞❩❫❵❭❯❱❳'
                 '⏝⎵⏟〞︶⏡﹂﹄︺︼︘﹀︾﹈︸〉⦒⧽﹚﹜﹞⁾₎⦌⦎⦐⁆⸣⸥⟆⦔⦖⸧⸩｠⧙⧛⸝⸍⸃⸅⸊᚜༻༽')
    stack = []
    for ch in msg.text:
        index = openbrckt.find(ch)
        if index >= 0:
            stack.append(index)
            continue
        index = clozbrckt.find(ch)
        if index >= 0:
            if stack and stack[-1] == index:
                stack.pop()
    closed = ''.join(reversed(tuple(map(clozbrckt.__getitem__, stack))))
    if closed:
        if len(closed) > 20:
            closed = closed[:20] + '…'
        return closed

@cp.register_handler('blackgun', mtype=('group',))
def ghd_blackgun(msg):
    '''
    Reply some messages that fit some conditions. (aka. Blackgun Handler)
    '''
    if not msg:
        return
    ...

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
