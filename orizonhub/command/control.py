#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .support import cp, logger

@cp.register_command('autoclose')
def cmd_autoclose(expr, msg=None):
    if msg and msg.mtype == 'group':
        if cp.config.command_config.get('autoclose'):
            cp.config.command_config['autoclose'] = False
            return 'Auto closing brackets disabled.'
        else:
            cp.config.command_config['autoclose'] = True
            return 'Auto closing brackets enabled.'

@cp.register_command('_cmd', protocol=('telegrambot',), dependency='sqlite')
def cmd__cmd(expr, msg=None):
    # TODO: verify admins
    if msg.mtype != 'private':
        return
    if expr == 'killserver':
        cp.external.restart()
        return 'Server restarted.'
    elif expr == 'commit':
        for v in cp.bus.loggers.values():
            v.commit()
        logger.info('DB committed upon user request.')
        return 'DB committed.'
    elif expr == 'raiseex':  # For debug
        raise Exception('/_cmd raiseex'))
    #else:
        #return 'ping'

#@cp.register_command('t2i')
#def cmd_t2i(expr, msg=None):
    #global CFG
    #if msg and msg.mtype == 'group':
        #if expr == 'off' or CFG.get('t2i'):
            #CFG['t2i'] = False
            #return 'Telegram to IRC forwarding disabled.'
        #elif expr == 'on' or not CFG.get('t2i'):
            #CFG['t2i'] = True
            #return 'Telegram to IRC forwarding enabled.'

#@cp.register_command('i2t')
#def cmd_i2t(expr, msg=None):
    #global CFG
    #if msg and msg.mtype == 'group':
        #if expr == 'off' or CFG.get('i2t'):
            #CFG['i2t'] = False
            #return 'IRC to Telegram forwarding disabled.'
        #elif expr == 'on' or not CFG.get('i2t'):
            #CFG['i2t'] = True
            #return 'IRC to Telegram forwarding enabled.'
