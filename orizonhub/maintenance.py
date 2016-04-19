#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging

from . import provider
from .ext import logfmt
from .utils import nt_from_dict
from .model import Message, User, UserType, Response

re_ircaction = re.compile('^\x01ACTION (.*)\x01$')
logger = logging.getLogger('maintenance')

def import_chatdig(filename, group, config, exportdb=None, fromtime=None, totime=None):
    irc_dest = User(None, 'irc', UserType.group, None, config.protocols.irc.channel,
                    config.protocols.irc.channel, None, config.group_name)
    sqlitelogger = provider.loggers['sqlite'](config.loggers.sqlite)
    logdb = logfmt.Messages(stream=True)
    logdb.media_format = None
    if exportdb:
        logdb.init_db(exportdb, 'cli')
        logdb.conn_cli = None
        logdb.db_cli.close()
        logdb.db_cli = None
        logdb.db_cli_ver = None
    logdb.init_db(filename, 'bot', True, group)
    peer = logdb.peers.find(group)
    chat = tg_make_user(peer)
    for k, obj in logdb.getmsgs(peer):
        if (fromtime and obj['date'] < fromtime or
            totime and obj['date'] > totime):
            continue
        if obj['mid'] > 0:
            reply = forward_from = forward_date = None
            if obj['msgtype'] == 're':
                reply = nt_from_dict(Message, {'protocol': 'telegrambot',
                                     'pid': obj['extra']['reply']['mid']})
            elif obj['msgtype'] == 'fwd':
                forward_from = tg_make_user(obj['extra']['fwd_src'])
                forward_date = obj['extra']['fwd_date']
            m = Message(
                None, 'telegrambot', obj['mid'],
                # from: Optional. Sender, can be empty for messages sent to channels
                tg_make_user(obj.get('from') or obj['chat']),
                chat, obj['text'], obj['media'] or None, obj['date'],
                forward_from, forward_date, reply, 'group', None
            )
            sqlitelogger.log(m)
        elif '_ircuser' in obj['media']:
            text = obj["text"]
            action = re_ircaction.match(text)
            media = None
            if action:
                text = action.group(1).strip()
                media = {'action': True}
            m = Message(
                None, 'irc', None, irc_make_user(obj['media']['_ircuser']),
                irc_dest, text, media, obj['date'], None, None, None, 'group', None
            )
            sqlitelogger.log(m)
    sqlitelogger.close()

def import_tgexport(filename, group, config, botdb=None, fromtime=None, totime=None):
    sqlitelogger = provider.loggers['sqlite'](config.loggers.sqlite)
    logdb = logfmt.Messages(stream=True)
    logdb.media_format = None
    logdb.init_db(filename, 'cli')
    if botdb:
        logdb.init_db(botdb, 'bot', True, group)
    peer = logdb.peers.find(group)
    chat = tg_make_user(peer)
    for k, obj in logdb.getmsgs(peer):
        if (fromtime and obj['date'] < fromtime or
            totime and obj['date'] > totime or
            obj['dest']['id'] != peer['id']):
            continue
        reply = forward_from = forward_date = None
        if obj['msgtype'] == 're':
            reply = nt_from_dict(Message, {'protocol': 'telegramcli',
                                 'pid': obj['extra']['reply']['mid']})
        elif obj['msgtype'] == 'fwd':
            forward_from = tg_make_user(obj['extra']['fwd_src'])
            forward_date = obj['extra']['fwd_date']
        m = Message(
            None, 'telegramcli', obj['mid'],
            # from: Optional. Sender, can be empty for messages sent to channels
            tg_make_user(obj.get('from') or obj['chat']),
            chat, obj['text'], obj['media'] or None, obj['date'],
            forward_from, forward_date, reply, 'group', None
        )
        sqlitelogger.log(m)
    sqlitelogger.close()


def tg_make_user(obj):
    if obj is None:
        return None
    if 'type' in obj:
        if obj['type'] == 'user':
            utype = UserType.user
            pid = obj['id']
        elif obj['type'] == 'chat':
            utype = UserType.group
            pid = -obj['id']
        elif obj['type'] == 'channel': # supergroup
            utype = UserType.group
            pid = -obj['id'] - 1000000000000
    else:
        utype = UserType.user
    return User(None, 'telegram', utype, pid, obj.get('username'),
                obj.get('first_name') or obj.get('title'),
                obj.get('last_name'), None)

def irc_make_user(nick, protocol='irc', realname=None, ident=None):
    # the ident is not used at present
    return User(None, protocol, UserType.user, None,
                nick, realname, None, nick.rstrip('_'))
