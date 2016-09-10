#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import copy
import json
import logging

from . import provider
from .ext import logfmt
from .utils import nt_from_dict
from .model import Message, User, UserType, Response

re_ircaction = re.compile('^\x01ACTION (.*)\x01$')
logger = logging.getLogger('maintenance')

def _identify_dup_msg(a, b):
    def user_equal(a, b):
        if a == b:
            return True
        elif a and b:
            return a.id == b.id
        else:
            return False

    def tgcli_media_equal(a: Message, b: Message):
        if a.media == b.media:
            return True
        elif a.media and b.media:
            am = copy.deepcopy(a.media)
            bm = copy.deepcopy(b.media)
            if a.protocol == 'telegrambot':
                media, action = media_bot2cli(a.text, a.media, True)
                am = media or action
            if b.protocol == 'telegrambot':
                media, action = media_bot2cli(b.text, b.media, True)
                bm = media or action
            if isinstance(am.get('user'), dict):
                am['user'] = am['user']['peer_id']
            if isinstance(bm.get('user'), dict):
                bm['user'] = bm['user']['peer_id']
            if am.get('type') == 'chat_created':
                del am['title']
            if bm.get('type') == 'chat_created':
                del bm['title']
            if am == bm:
                return True
            else:
                # logger.debug('Media comparison unequal: %s, %s | %s, %s', a.media, b.media, am, bm)
                return False
        else:
            return False

    proto_order = {v:n for n,v in enumerate(('telegrambot', 'irc', 'telegramcli'))}
    a, b = sorted((a, b), key=lambda x: proto_order.get(x.protocol, 100))
    if a.pid == b.pid and a.chat.id == b.chat.id:
        # telegrambot and telegrambot/cli (supergroup)
        return a
    elif (a.src.id == b.src.id and
          a.chat.id == b.chat.id and
          a.text == b.text and
          user_equal(a.fwd_src, b.fwd_src) and
          tgcli_media_equal(a, b)):
        # telegrambot and telegrambot/cli (group)
        return a
    elif (a.protocol == 'irc' and b.protocol == 'telegramcli' and b.text and
          b.text[0] in '[*' and a.text in b.text):
        return a

def _msg_dedup(messages):
    MAX_INTV = 4
    queue = []
    for msg in messages:
        queue_new = []
        for msg2 in queue:
            if msg2.time < msg.time - MAX_INTV:
                yield msg2
            else:
                result = _identify_dup_msg(msg, msg2)
                if result:
                    queue_new.append(result)
                    break
                else:
                    queue_new.append(msg2)
        else:
            queue_new.append(msg)
        queue = queue_new
    yield from queue

def import_to_db(dbs, config, sort=False):
    sqlitelogger = provider.loggers['sqlite'](config.loggers.sqlite)
    sqlitelogger.autocommit = False
    messages = []
    for dbtask in dbs:
        dbtask = dbtask.copy()
        dbtype = dbtask.pop('type')
        logger.info('Processing: ' + dbtype)
        if dbtype == 'chatdig':
            msgiter = _import_chatdig(config=config, **dbtask)
        elif dbtype == 'tgexport':
            msgiter = _import_tgexport(config=config, **dbtask)
        for msg in msgiter:
            if sort:
                messages.append(msg)
            else:
                sqlitelogger.log(msg)
    if sort:
        messages.sort(key=lambda m: (m.time, m.pid or 0))
        for msg in _msg_dedup(messages):
            sqlitelogger.log(msg)
    sqlitelogger.close()

def _import_chatdig(filename, group, config, exportdb=None, fromtime=None, totime=None):
    irc_dest = User(None, 'irc', UserType.group, None, config.protocols.irc.channel,
                    config.protocols.irc.channel, None, config.group_name)
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
                tg_make_user(obj.get('src') or obj['dest']),
                chat, obj['text'], obj['media'] or None, obj['date'],
                forward_from, forward_date, reply, 'group', None
            )
            yield m
        elif '_ircuser' in obj['media']:
            text = obj["text"] or ''
            action = re_ircaction.match(text)
            media = None
            if action:
                text = action.group(1).strip()
                media = {'action': True}
            m = Message(
                None, 'irc', None, irc_make_user(obj['media']['_ircuser']), irc_dest,
                text, media, obj['date'], None, None, None, 'group', obj["text"]
            )
            yield m

def _import_tgexport(filename, group, config, botdb=None, fromtime=None, totime=None):
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
            tg_make_user(obj.get('src') or obj['dest']),
            chat, obj['text'], obj['media'] or obj['action'] or None, obj['date'],
            forward_from, forward_date, reply, 'group', None
        )
        yield m


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

def media_bot2cli(text, media=None, strict=False):
    # Copied from logfmt.py
    unkuser = lambda user: {
        'peer_id': user['id'],
        'first_name': user['first_name'],
        'last_name': user.get('last_name'),
        'username': user.get('username'),
        'type': 'user'
    }

    if not media:
        return None, None
    dm = {}
    da = {}

    mt = None

    if '_ircuser' in media and not strict:
        dm['_ircuser'] = media['_ircuser']
    if mt and not strict:
        dm.update(media[mt])

    if ('audio' in media or 'document' in media
        or 'sticker' in media or 'video' in media
        or 'voice' in media):
        if strict:
            dm['type'] = 'document'
        else:
            dm['type'] = mt or 'document'
    elif 'photo' in media:
        dm['type'] = 'photo'
        dm['caption'] = text or ''
    elif 'contact' in media:
        dm['type'] = 'contact'
        dm['phone'] = media['contact']['phone_number']
        dm['first_name'] = media['contact']['first_name']
        dm['last_name'] = media['contact'].get('last_name')
        dm['user_id'] = media['contact'].get('user_id')
    elif 'location' in media:
        dm['type'] = 'geo'
        dm['longitude'] = media['location']['longitude']
        dm['latitude'] = media['location']['latitude']
    elif 'venue' in media:
        dm['type'] = 'venue'
        dm['longitude'] = media['venue']['location']['longitude']
        dm['latitude'] = media['venue']['location']['latitude']
        if media['venue']['title']:
            dm['type'] = media['venue']['title']
        dm['address'] = media['venue']['address']
        if 'foursquare_id' in media['venue']:
            dm['provider'] = 'foursquare'
            dm['venue_id'] = media['venue']['foursquare_id']
    elif 'new_chat_participant' in media:
        user = media['new_chat_participant']
        da['type'] = 'chat_add_user'
        da['user'] = unkuser(user)
    elif 'left_chat_participant' in media:
        user = media['left_chat_participant']
        da['type'] = 'chat_del_user'
        da['user'] = unkuser(user)
    elif 'new_chat_title' in media:
        da['type'] = 'chat_rename'
        da['title'] = media['new_chat_title']
    elif 'new_chat_photo' in media:
        da['type'] = 'chat_change_photo'
    elif 'delete_chat_photo' in media:
        da['type'] = 'chat_delete_photo'
    elif 'group_chat_created' in media:
        da['type'] = 'chat_created'
        da['title'] = ''
    return dm or None, da or None
