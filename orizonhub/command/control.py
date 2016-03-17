#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .support import cp

@cp.register_command('autoclose')
def cmd_autoclose(expr, msg=None):
    global CFG
    if msg['chat']['id'] == -CFG['groupid']:
        if CFG.get('autoclose'):
            CFG['autoclose'] = False
            return 'Auto closing brackets disabled.'
        else:
            CFG['autoclose'] = True
            return 'Auto closing brackets enabled.'

@cp.register_command('_cmd', protocol=('telegrambot',), dependency='sqlite')
def cmd__cmd(expr, msg=None):
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

#@cp.register_command('t2i')
#def cmd_t2i(expr, msg=None):
    #global CFG
    #if msg['chat']['id'] == -CFG['groupid']:
        #if expr == 'off' or CFG.get('t2i'):
            #CFG['t2i'] = False
            #return 'Telegram to IRC forwarding disabled.'
        #elif expr == 'on' or not CFG.get('t2i'):
            #CFG['t2i'] = True
            #return 'Telegram to IRC forwarding enabled.'

#@cp.register_command('i2t')
#def cmd_i2t(expr, msg=None):
    #global CFG
    #if msg['chat']['id'] == -CFG['groupid']:
        #if expr == 'off' or CFG.get('i2t'):
            #CFG['i2t'] = False
            #return 'IRC to Telegram forwarding disabled.'
        #elif expr == 'on' or not CFG.get('i2t'):
            #CFG['i2t'] = True
            #return 'IRC to Telegram forwarding enabled.'

@cp.register_command('_cmd', protocol=('telegrambot',), dependency='sqlite')
def cmd__welcome(expr, msg=None):
    if chatid > 0:
        return
    usr = msg["new_chat_participant"]
    USER_CACHE[usr["id"]] = (usr.get("username"), usr.get("first_name"), usr.get("last_name"))
    return '欢迎 %s 加入本群！' % dc_getufname(usr)

