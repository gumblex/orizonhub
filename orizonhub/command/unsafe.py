#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .support import cp

@cp.register_command('calc', enabled=False)
def cmd_calc(expr, msg=None):
    '''/calc <expr> Calculate <expr>.'''
    # Too many bugs
    if expr:
        return cp.external('calc', expr).result()
    else:
        return 'Syntax error. Usage: ' + cmd_calc.__doc__

@cp.register_command('py', enabled=True)
def cmd_py(expr, msg=None):
    '''/py <expr> Evaluate Python 2 expression <expr>.'''
    if expr:
        if len(expr) > 1000:
            return 'Expression too long.'
        else:
            return cp.external('py', expr).result()
    else:
        return 'Syntax error. Usage: ' + cmd_py.__doc__

@cp.register_command('query', mtype=('private',), dependency='sqlite')
def cmd_query(expr, msg=None):
    # no public docs
    __doc__ = '''/query [SQL] Execute SQL query.'''
    if expr:
        return cp.external('query', expr).result()
    else:
        return 'Syntax error. Usage: ' + __doc__
