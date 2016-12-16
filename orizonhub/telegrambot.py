#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import logging

from .model import __version__, Protocol, Message, User, UserType, Response
from .utils import mdescape, timestring_a, smartname, fwd_to_text, sededit, LimitedSizeDict

import requests

logger = logging.getLogger('tgbot')

re_ircfmt = re.compile('([\x02\x1D\x1F\x16\x0F\x06]|\x03(?:\d+(?:,\d+)?)?)')
re_http = re.compile(r'^\s*(ht|f)tps?://')

def ircfmt2tgmd(s):
    '''
    Convert IRC format code to Telegram Bot API style Markdown below:
        *bold text*
        _italic text_
        [text](URL)
        `inline fixed-width code`
        ```pre-formatted fixed-width code block```
    '''
    table = ('\x02\x16\x1D\x1F\x03', '**__*')
    # bold, reverse, italics, underline, color
    state = [False]*5
    code = ''
    ret = []
    for chunk in re_ircfmt.split(s):
        if not chunk:
            pass
        elif chunk[0] in table[0]:
            idx = table[0].index(chunk[0])
            if chunk[0] == '\x03':
                state[idx] = bool(chunk[1:])
            else:
                state[idx] = not state[idx]
            newcode = ''
            for k, v in enumerate(state):
                if v:
                    newcode = table[1][k]
                    break
            if code != newcode:
                if ret and ret[-1] == code:
                    ret.pop()
                else:
                    ret.append(code)
                ret.append(newcode)
                code = newcode
        elif chunk[0] == '\x0F':
            state = [False]*5
            ret.append(code)
            code = ''
        elif chunk[0] == '\x06':
            # blink
            pass
        elif code:
            # Telegram don't support escape within a format code
            if re_http.match(chunk):
                ret.pop()
                code = ''
            ret.append(chunk)
        else:
            ret.append(mdescape(chunk))
    if code:
        ret.append(code)
    return ''.join(ret)

class BotAPIFailed(Exception):
    pass

class TelegramBotProtocol(Protocol):
    # media fields may change in the future, so use the inverse.
    STATIC_FIELDS = frozenset(('message_id', 'from', 'date', 'chat', 'forward_from',
                    'forward_date', 'reply_to_message', 'text', 'caption'))
    METHODS = frozenset((
        'getMe', 'sendMessage', 'forwardMessage', 'sendPhoto', 'sendAudio',
        'sendDocument', 'sendSticker', 'sendVideo', 'sendVoice', 'sendLocation',
        'sendChatAction', 'getUserProfilePhotos', 'getUpdates', 'setWebhook',
        'getFile', 'answerInlineQuery'
    ))
    BotAPIFailed = BotAPIFailed

    def __init__(self, config, bus):
        self.config = config
        self.cfg = config.protocols.telegrambot
        self.bus = bus
        self.pastebin = bus.pastebin
        self.url = 'https://api.telegram.org/bot%s/' % self.cfg.token
        self.url_file = 'https://api.telegram.org/file/bot%s/' % self.cfg.token
        self.hsession = requests.Session()
        self.useragent = 'OrizonHub/%s %s' % (__version__, self.hsession.headers["User-Agent"])
        self.hsession.headers["User-Agent"] = self.useragent
        self.run = True
        # If you're sending bulk notifications to multiple users, the API will not
        # allow more than 30 messages per second or so. Consider spreading out
        # notifications over large intervals of 8—12 hours for best results.
        # Also note that your bot will not be able to send more than 20 messages
        # per minute to the same group.
        self.rate = 20/60 # 1/30
        self.attempts = 2
        self.last_sent = 0
        # updated later
        self.identity = User(None, 'telegram', UserType.user,
                             int(self.cfg.token.split(':')[0]), self.cfg.username,
                             config.bot_fullname, None, config.bot_nickname)
        # auto updated
        self.dest = User(None, 'telegram', UserType.group, self.cfg.groupid,
                         None, config.group_name, None, config.group_name)
        self.msghistory = LimitedSizeDict(size_limit=10)

    def start_polling(self):
        self.identity = self._make_user(self.bot_api('getMe'))
        self.cfg.username = self.identity.username
        # reload usernames
        self.bus.handler.usernames = set(p.username for p in
            self.bus.handler.config.protocols.values() if 'username' in p)
        if 'sqlite' in self.bus.handler.loggers:
            self.identity = self.bus.sqlite.update_user(self.identity)
        while self.run:
            logger.debug('tgapi.offset: %s',
                self.bus.handler.state.get('tgapi.offset', 0))
            try:
                updates = self.bot_api('getUpdates',
                    offset=self.bus.handler.state.get('tgapi.offset', 0), timeout=10)
            except Exception:
                logging.exception('TelegramBot: Get updates failed.')
                continue
            if updates:
                logging.debug('TelegramBot: messages coming.')
                maxupd = 0
                for upd in updates:
                    maxupd = max(maxupd, upd['update_id'])
                    if 'message' in upd:
                        self.bus.post(self._make_message(upd['message'], True))
                    elif 'edited_message' in upd:
                        self.bus.post(self._make_message(upd['edited_message'], True))
                self.bus.handler.state['tgapi.offset'] = maxupd + 1
            time.sleep(.2)

    def send(self, response: Response, protocol: str, forwarded: Message) -> Message:
        rinfo = response.info or {}
        kwargs = rinfo.get('telegrambot', {})
        kwargs.update(rinfo.get('media', {}))
        text = response.text
        if response.reply.protocol.startswith('telegram'):
            kwargs['reply_to_message_id'] = response.reply.pid
            withreplysrc = False
            chat_id = response.reply.chat.pid
        elif forwarded:
            kwargs['reply_to_message_id'] = forwarded.pid
            withreplysrc = False
            chat_id = forwarded.chat.pid
        else:
            withreplysrc = True
            chat_id = self.dest.pid
        rtype = rinfo.get('type')
        if rtype == 'markdown':
            kwargs['parse_mode'] = 'Markdown'
        # we have handled this in commands
        #elif rtype == 'forward':
            #fmsgs = rinfo['messages']
            #if (len(fmsgs) == 1 and fmsgs[0].pid
                #and fmsgs[0].protocol.startswith('telegram')):
                #try:
                    #m = self.bot_api('forwardMessage',
                        #chat_id=response.reply.chat.pid,
                        #from_chat_id=fmsgs[0].chat.id, message_id=fmsgs[0].pid,
                        #disable_notification=kwargs.get('disable_notification'))
                    #return self._make_message(m)
                #except BotAPIFailed:
                    #pass
            #text = fwd_to_text(fmsgs, self.bus.timezone)
        elif rtype in ('photo', 'audio', 'document', 'sticker', 'video', 'voice'):
            fn = rinfo['media'].get('_file')
            if fn:
                input_file = {rtype: (os.path.basename(fn), open(fn, 'rb'))}
            else:
                # kwargs[rtype] must be filled
                input_file = None
            m = self.bot_api('send' + rtype.capitalize(),
                chat_id=response.reply.chat.pid, input_file=input_file, **kwargs)
            return self._make_message(m)
        elif rtype == 'location':
            m = self.bot_api('sendLocation',
                chat_id=response.reply.chat.pid, **kwargs)
            return self._make_message(m)
        if withreplysrc:
            text = '%s: %s' % (smartname(response.reply.src), text)
        m = self.sendmsg(text, chat_id, **kwargs)
        return self._make_message(m)

    def forward(self, msg: Message, protocol: str) -> Message:
        if protocol.startswith('telegram'):
            try:
                m = self.bot_api('forwardMessage', chat_id=self.dest.pid,
                    from_chat_id=msg.chat.id, message_id=msg.pid)
                return self._make_message(m)
            except BotAPIFailed:
                pass
        parse_mode = None
        if msg.fwd_src:
            text = '[%s] Fwd %s: %s' % (smartname(msg.src), smartname(msg.fwd_src), msg.text)
        elif msg.reply:
            text = '[%s] %s: %s' % (smartname(msg.src), smartname(msg.reply.src), msg.text)
        elif re_ircfmt.search(msg.text):
            content = ircfmt2tgmd(msg.text)
            try:
                content = self.bus.irc.identify_mention(content, True)
            except KeyError:
                pass
            text = '\\[%s] %s' % (smartname(msg.src), content)
            parse_mode = 'Markdown'
        else:
            text = '[%s] %s' % (smartname(msg.src), msg.alttext or msg.text)
        m = self.bot_api('sendMessage', chat_id=self.dest.pid, text=text,
            parse_mode=parse_mode)
        return self._make_message(m)

    def status(self, dest, action):
        return self.bot_api('sendChatAction', chat_id=dest.pid, action=action)

    def close(self):
        self.run = False

    def bot_api(self, method, input_file=None, **params):
        wait = self.rate - time.perf_counter() + self.last_sent
        if wait > 0:
            time.sleep(wait)
        att = 1
        ret = None
        while att <= self.attempts and self.run:
            try:
                req = self.hsession.post(self.url + method, data=params,
                                         files=input_file,
                                         timeout=(params.get('timeout', 0)+20))
                retjson = req.content
                ret = json.loads(retjson.decode('utf-8'))
                break
            except Exception as ex:
                if att < self.attempts:
                    time.sleep((att+1) * 2)
                    self.change_session()
                else:
                    raise ex
            att += 1
        self.last_sent = time.perf_counter()
        if ret is None:
            raise BotAPIFailed('attempt = %s, self.run = %s', att, self.run)
        elif not ret['ok']:
            raise BotAPIFailed(str(ret))
        return ret['result']

    def sendmsg(self, text, chat_id, reply_to_message_id=None, **kwargs):
        text = text.strip()
        if not text:
            logging.warning('Empty message ignored: %s, %s' % (chat_id, reply_to_message_id))
            return
        logging.info('sendMessage(%s): %s' % (len(text), text[:20]))
        # 0-4096 characters.
        if len(text) > 2048:
            text = text[:2047] + '…'
        reply_id = reply_to_message_id or None
        return self.bot_api('sendMessage', chat_id=chat_id, text=text, reply_to_message_id=reply_id, **kwargs)

    def __getattr__(self, name):
        if name in self.METHODS:
            return lambda **kwargs: self.bot_api(name, **kwargs)
        else:
            raise AttributeError

    def _parse_media(self, media):
        mt = media.keys() & frozenset(('audio', 'document', 'sticker', 'video', 'voice'))
        file_ext = ''
        if mt:
            mt = mt.pop()
            file_id = media[mt]['file_id']
            file_size = media[mt].get('file_size')
            if mt == 'sticker':
                file_ext = '.webp'
        elif 'photo' in media:
            photo = max(media['photo'], key=lambda x: x['width'])
            file_id = photo['file_id']
            file_size = photo.get('file_size')
            file_ext = '.jpg'
        else:
            return None
        logging.debug('getFile: %r' % file_id)
        if self.config.services.pastebin:
            fp = self.bot_api('getFile', file_id=file_id)
            file_size = fp.get('file_size') or file_size or 0
            file_path = fp.get('file_path')
            if not file_path:
                raise BotAPIFailed("can't get file_path for " + file_id)
            file_ext = os.path.splitext(file_path)[1] or file_ext
            cachename = file_id + file_ext
            return (self.url_file + file_path, cachename, file_size)
        else:
            return ('', '', 0)

    def servemedia(self, media):
        '''
        Reply type and link of media. This only generates links for photos.
        '''
        if not media:
            return ''
        media_type = tuple((k,v) for k,v in media.items() if k not in ('forward_from_chat', 'entities', 'edit_date'))
        if media_type:
            ftype, fval = media_type[0]
        else:
            return ''
        ret = '<%s>' % ftype
        if 'new_chat_title' in media:
            ret += ' ' + media['new_chat_title']
        else:
            if ftype == 'document':
                ret += ' %s' % (fval.get('file_name', ''))
            elif ftype in ('video', 'voice'):
                ret += ' ' + timestring_a(fval.get('duration', 0))
            elif ftype == 'location':
                ret += ' https://www.openstreetmap.org/?mlat=%s&mlon=%s' % (
                        fval['latitude'], fval['longitude'])
            elif ftype == 'venue':
                ret += ' %s, %s' % (fval['title'], fval['address'])
                if fval.get('foursquare_id'):
                    ret += ' http://foursquare.com/venue/' + fval['foursquare_id']
                else:
                    ret += ' https://www.openstreetmap.org/?mlat=%s&mlon=%s' % (
                        fval['location']['latitude'], fval['location']['longitude'])
            elif ftype == 'sticker' and fval.get('emoji'):
                ret = fval['emoji'] + ' ' + ret
            try:
                ret += ' ' + self.bus.pastebin.paste_url(*self._parse_media(media))
            except (TypeError, NotImplementedError):
                # _parse_media returned None
                pass
            except Exception:
                # ValueError, FileNotFoundError or network problems
                logging.exception("can't paste a file: %s", media)
        return ret

    def _make_message(self, obj, memorize=False):
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
        text = text2 = obj.get('text') or obj.get('caption', '')
        alttext = self.servemedia(media)
        if 'edit_date' in media:
            origtext = self.msghistory.get(obj['message_id'])
            if origtext and '\n' not in text:
                text2 = '<edit: %s>' % sededit(origtext, text)
            else:
                text2 = '<edit> ' + text
        if text and memorize:
            self.msghistory[obj['message_id']] = text
        if alttext and text2:
            alttext = text2 + ' ' + alttext
        elif text2 != text:
            alttext = text2
        return Message(
            None, 'telegrambot', obj['message_id'],
            # from: Optional. Sender, can be empty for messages sent to channels
            self._make_user(obj.get('from') or obj['chat']),
            chat, text, media, obj['date'],
            self._make_user(obj.get('forward_from')), obj.get('forward_date'),
            self._make_message(obj.get('reply_to_message')), mtype, alttext or None
        )

    @staticmethod
    def _make_user(obj):
        if obj is None:
            return None
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
