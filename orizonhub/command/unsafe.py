#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .support import cp

@cp.register_command('calc')
def cmd_calc(expr, msg=None):
    '''/calc <expr> Calculate <expr>.'''
    # Too many bugs
    if expr:
        cp.external('calc', expr)
    else:
        return 'Syntax error. Usage: ' + cmd_calc.__doc__

@cp.register_command('py', enabled=False)
def cmd_py(expr, msg=None):
    '''/py <expr> Evaluate Python 2 expression <expr>.'''
    if expr:
        if len(expr) > 1000:
            return 'Expression too long.'
        else:
            cp.external('py', expr)
    else:
        return 'Syntax error. Usage: ' + cmd_py.__doc__
