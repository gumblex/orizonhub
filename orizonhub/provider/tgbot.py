#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import requests
from .base import *

socket.setdefaulttimeout(60)

def retrieve(url, filename, raisestatus=True):
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    if raisestatus:
        r.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
        f.flush()
    return r.status_code

class TelegramBotAPIFailed(Exception):
    pass

class TelegramBotProtocal(MessageProtocal):

    name = 'tgbot'

    def setup(self, host):
        super().__init__()
        self.offset = host.sqlite.execute('SELECT val FROM config WHERE id = 0').fetchone()
        self.offset = self.offset[0] if self.offset else 0
        self.HSession = requests.Session()
        self.useragent = 'TgChatDiggerBot/%s %s' % (__version__, self.HSession.headers["User-Agent"])
        self.HSession.headers["User-Agent"] = useragent
        self.msg_cache = LRUCache(20)
        self.user_cache = LRUCache(10)
        self.running = True

    def bot_api(method, **params):
        for att in range(3):
            if self.host.stop.is_set():
                raise TelegramBotAPIFailed('Exiting.')
            try:
                req = self.HSession.get(URL + method, params=params, timeout=45)
                retjson = req.content
                ret = json.loads(retjson.decode('utf-8'))
                break
            except Exception as ex:
                if att < 1:
                    time.sleep((att+1) * 2)
                else:
                    raise ex
        if not ret['ok']:
            raise TelegramBotAPIFailed(repr(ret))
        return ret['result']

    def sendmsg(self, text, chat_id, reply_to_message_id=None):
        global LOG_Q
        text = text.strip()
        if not text:
            logging.warning('Empty message ignored: %s, %s' % (chat_id, reply_to_message_id))
            return
        logging.info('sendMessage(%s): %s' % (len(text), text[:20]))
        if len(text) > 2000:
            text = text[:1999] + '…'
        reply_id = reply_to_message_id
        if reply_to_message_id and reply_to_message_id < 0:
            reply_id = None
        m = bot_api('sendMessage', chat_id=chat_id, text=text, reply_to_message_id=reply_id)
        if chat_id == -CFG['groupid']:
            MSG_CACHE[m['message_id']] = m
            # IRC messages
            if reply_to_message_id is not None:
                LOG_Q.put(m)
                irc_send(text, reply_to_message_id)
        return m

    def forward(self, message_id, chat_id, reply_to_message_id=None):
        global LOG_Q
        logging.info('forwardMessage: %r' % message_id)
        try:
            if message_id < 0:
                raise ValueError('Invalid message id')
            r = bot_api('forwardMessage', chat_id=chat_id, from_chat_id=-CFG['groupid'], message_id=message_id)
            logging.debug('Forwarded: %s' % message_id)
        except (ValueError, BotAPIFailed) as ex:
            m = db_getmsg(message_id)
            if m:
                r = sendmsg('[%s] %s: %s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(m[4] + CFG['timezone'] * 3600)), db_getufname(m[1]), m[2]), chat_id, reply_to_message_id)
                logging.debug('Manually forwarded: %s' % message_id)
        if chat_id == -CFG['groupid']:
            LOG_Q.put(r)
            irc_send(forward_message_id=message_id)

    def forwardmulti(self, message_ids, chat_id, reply_to_message_id=None):
        failed = False
        message_ids = tuple(message_ids)
        for message_id in message_ids:
            logging.info('forwardMessage: %r' % message_id)
            try:
                if message_id < 0:
                    raise ValueError('Invalid message id')
                r = bot_api('forwardMessage', chat_id=chat_id, from_chat_id=-CFG['groupid'], message_id=message_id)
                logging.debug('Forwarded: %s' % message_id)
            except (ValueError, BotAPIFailed) as ex:
                failed = True
                break
        if failed:
            forwardmulti_t(message_ids, chat_id, reply_to_message_id)
            logging.debug('Manually forwarded: %s' % (message_ids,))
        elif chat_id == -CFG['groupid']:
            for message_id in message_ids:
                irc_send(forward_message_id=message_id)

    def forwardmulti_t(self, message_ids, chat_id, reply_to_message_id=None):
        text = []
        for message_id in message_ids:
            m = db_getmsg(message_id)
            if m:
                text.append('[%s] %s: %s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(m[4] + CFG['timezone'] * 3600)), db_getufname(m[1]), m[2]))
        sendmsg('\n'.join(text) or 'Message(s) not found.', chat_id, reply_to_message_id)

    @async_method
    def typing(self, chat_id):
        logging.info('sendChatAction: %r' % chat_id)
        bot_api('sendChatAction', chat_id=chat_id, action='typing')

    def getfile(self, file_id):
        logging.info('getFile: %r' % file_id)
        return bot_api('getFile', file_id=file_id)

    def run(self):
        while not self.host.stop.wait(.2):
            try:
                updates = bot_api('getUpdates', offset=self.offset, timeout=10)
            except Exception as ex:
                logging.exception('Get updates failed.')
                continue
            if updates:
                logging.debug('Messages coming.')
                self.offset = updates[-1]["update_id"] + 1
                for upd in updates:
                    self.processmsg(upd)

    def classify(self, msg):
        '''
        Classify message type:

        - Command: (0)
                All messages that start with a slash ‘/’ (see Commands above)
                Messages that @mention the bot by username
                Replies to the bot's own messages

        - Group message (1)
        - IRC message (2)
        - new_chat_participant (3)
        - Ignored message (10)
        - Invalid calling (-1)
        '''
        chat = msg['chat']
        text = msg.get('text', '').strip()
        if text:
            if text[0] in "/'" or ('@' + CFG['botname']) in text:
                return 0
            elif 'first_name' in chat:
                return 0
            else:
                reply = msg.get('reply_to_message')
                if reply and reply['from']['id'] == CFG['botid']:
                    return 0

        # If not enabled, there won't be this kind of msg
        ircu = msg.get('_ircuser')
        if ircu and ircu != CFG['ircnick']:
            return 2

        if 'title' in chat:
            # Group chat
            if 'new_chat_participant' in msg:
                return 3
            if chat['id'] == -CFG['groupid']:
                if msg['from']['id'] == CFG['botid']:
                    return 10
                else:
                    return 1
            else:
                return 10
        else:
            return -1

    @async_method
    def processmsg(self, d):
        logging.debug('Msg arrived: %r' % d)
        uid = d['update_id']
        if 'message' in d:
            msg = d['message']
            if 'text' in msg:
                msg['text'] = msg['text'].replace('\xa0', ' ')
            elif 'caption' in msg:
                msg['text'] = msg['caption'].replace('\xa0', ' ')
            self.msg_cache[msg['message_id']] = msg
            cls = classify(msg)
            logging.debug('Classified as: %s', cls)
            try:
                ret = self.host.newmsg(Message(msg, self.name, i=cls))
            except Exception as ex:
                logging.exception('Failed to process a message.')
            if ret is NotImplemented:
                if chatid > 0:
                    self.sendmsg('Invalid command. Send /help for help.', msg['chat']['id'], msg['message_id'])
            elif ret is not None:
                self.sendmsg(ret, msg['chat']['id'], msg['message_id'])
