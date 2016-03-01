#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging

from . import tgcli
from ..model import __version__, Protocol, Message, User, UserType

import requests

class BotAPIFailed(Exception):
    pass

class TelegramBotProtocol(Protocol):
    # media fields may change in the future, so use the inverse.
    STATIC_FIELDS = frozenset(('message_id', 'from', 'date', 'chat', 'forward_from',
                    'forward_date', 'reply_to_message', 'text', 'caption'))

    def __init__(self, config, bus):
        self.config = config
        self.cfg = config.protocols.telegramcli
        self.bus = bus
        self.pastebin = bus.pastebin
        self.url = 'https://api.telegram.org/bot%s/' % self.cfg.token
        self.url_file = 'https://api.telegram.org/file/bot%s/' % self.cfg.token
        self.hsession = requests.Session()
        self.useragent = 'OrizonHub/%s %s' % (__version__, self.hsession.headers["User-Agent"])
        self.hsession.headers["User-Agent"] = self.useragent
        self.run = True
        self.rate = 1/2
        self.attempts = 2
        self.last_sent = 0
        # updated later
        self.identity = User(None, 'telegramcli', UserType.user,
                             int(self.cfg.token.split(':')), self.cfg.username,
                             config.bot_fullname, None, config.bot_nickname)
        # auto updated
        self.dest = User(None, 'telegramcli', UserType.group, self.cfg.groupid,
                         None, config.group_name, None, config.group_name)

    def start_polling(self):
        while self.run:
            try:
                updates = bot_api('getUpdates', offset=self.bus.state.get('tgbot.offset', 0), timeout=10)
            except Exception as ex:
                logging.exception('TelegramBot: Get updates failed.')
                continue
            if updates:
                logging.debug('TelegramBot: messages coming.')
                self.bus.state['tgapi.offset'] = updates[-1]["update_id"] + 1
                for upd in updates:
                    self.bus.post(upd)
            time.sleep(.2)

    def bot_api(self, method, **params):
        att = 1
        while att <= self.attempts and self.run:
            try:
                req = HSession.get(self.url + method, params=params, timeout=45)
                retjson = req.content
                ret = json.loads(retjson.decode('utf-8'))
                break
            except Exception as ex:
                if att < self.attempts:
                    time.sleep((att+1) * 2)
                    change_session()
                else:
                    raise ex
            att += 1
        if not ret['ok']:
            raise BotAPIFailed(str(ret))
        return ret['result']

    def servemedia(self, msg):
        ## TODO
        '''
        Reply type and link of media. This only generates links for photos.
        '''
        keys = tuple(media.keys() & MEDIA_TYPES)
        if not keys:
            return ''
        ret = '<%s>' % keys[0]
        if 'photo' in media:
            servemode = CFG.get('servemedia')
            if servemode:
                fname, code = cachemedia(media)
                if servemode == 'self':
                    ret += ' %s%s' % (CFG['serveurl'], fname)
                elif servemode == 'vim-cn':
                    r = requests.post('http://img.vim-cn.com/', files={'name': open(os.path.join(CFG['cachepath'], fname), 'rb')})
                    ret += ' ' + r.text
        elif 'document' in media:
            ret += ' %s type: %s' % (media['document'].get('file_name', ''), media['document'].get('mime_type', ''))
        elif 'video' in media:
            ret += ' ' + timestring_a(media['video'].get('duration', 0))
        elif 'voice' in media:
            ret += ' ' + timestring_a(media['voice'].get('duration', 0))
        elif 'new_chat_title' in media:
            ret += ' ' + media['new_chat_title']
        return ret

    @staticmethod
    def _make_message(obj):
        if obj is None:
            return None
        chat = self._make_user(obj['chat'])
        media = {k:obj[k] for k in frozenset(obj.keys()).difference(self.STATIC_FIELDS)}
        if chat.pid == self.dest.pid:
            self.dest = chat
            mtype = 'group'
        elif chat.type == UserType.user:
            mtype = 'private'
        else:
            # other group or channel
            mtype = 'othergroup'
        if media:
            alttext
        return Message(
            'telegrambot', obj['message_id'],
            # from: Optional. Sender, can be empty for messages sent to channels
            self._make_user(obj.get('from') or obj['chat']), chat,
            obj.get('text') or obj.get('caption', ''), media, date,
            self._make_user(obj.get('forward_from')), obj.get('forward_date'),
            self._make_message(obj.get('reply_to_message')), mtype, alttext
        )

    @staticmethod
    def _make_user(obj):
        if obj is None:
            return None
        # the ident is not used at present
        if 'type' in obj:
            if obj['type'] == 'private':
                utype = UserType.user
            elif obj['type'] in ('group', 'supergroup'):
                utype = UserType.group
            else:
                utype = UserType.channel
        else:
            utype = UserType.user        
        return User(None, 'telegram', utype, obj['id'], obj.get('username'),
                    obj.get('first_name') or obj.get('title'),
                    obj.get('last_name'), None)

    def change_session(self):
        self.hsession.close()
        self.hsession = requests.Session()
        self.hsession.headers["User-Agent"] = self.useragent
        logging.warning('Session changed.')

    def close(self):
        self.run = False
