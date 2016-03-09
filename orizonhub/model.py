#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import enum
import collections

__version__ = '2.0'

Message = collections.namedtuple('Message', (
    'id',       # Message id as in database: int or None (unknown)
    'protocol', # Protocol name: str ('telegrambot', 'irc', ...)
    # Protocol in User use 'telegrambot' and 'telegramcli' because of
    # incompatible 'media' format
    'pid',      # Protocol-specified message id: (positive) int or None
    'src',      # 'From' field: User
    'chat',     # Conversation the message belongs to: User
    'text',     # Message text: str
    'media',    # Extra information about media and service info: dict or None
    'time',     # Message time or receive time: int (unix timestamp)
    'fwd_src',  # Forwarded from (Telegram): User or None
    'fwd_time', # Forwarded message time (Telegram): int (unix timestamp) or None
    'reply',    # Reply message: Message or None
    'mtype',    # Protocol provider set: 'group', 'othergroup' or 'private'
    'alttext'   # Protocol provider set, for media contents: str or None
))

Request = collections.namedtuple('Request', ('cmd', 'expr', 'kwargs'))

class User(collections.namedtuple('User', (
        'id',         # User id as in database: int or None (unknown)
        'protocol',   # Protocol name: str ('telegram', 'irc', ...)
        # Protocol in User use 'telegram' as generic name
        'type',       # Protocol-specified type: UserType
        # Telegram:      user, group (contains 'supergroup'), channel
        # IRC and other: user, group
        'pid',        # Protocol-specified message id: int or None
        'username',   # Protocol-specified username: str or None
        'first_name', # Protocol-specified first name or full name: str or None
        'last_name',  # Protocol-specified last name: str or None
        'alias'       # Canonical name alias: str or None
    ))):
    UnameKey = collections.namedtuple('UnameKey', ('protocol', 'username'))
    PidKey = collections.namedtuple('PidKey', ('protocol', 'pid'))
    def _key(self):
        if self.pid is None:
            return self.UnameKey(self.protocol, self.username)
        else:
            return self.PidKey(self.protocol, self.pid)

class UserType(enum.IntEnum):
    user = 1
    group = 2
    # to be compatible with tg-cli
    channel = 5

Command = collections.namedtuple('Command',
                                 ('func', 'usage', 'protocol', 'dependency'))
Response = collections.namedtuple('Response', (
    'text', # Reply text: str
    # Can be ignored if 'info' has better description of the response
    'info', # Other info or structured answer: dict or None
    # This 'info' contains necessary information to rebuild a message to send out
    # Fields definition:
    # 'type' field: -> str
    #  * 'markdown': Response.text is Markdown
    #  * 'forward': must then contain a 'messages' field
    #  * 'photo', 'audio', 'document', 'sticker', 'video', 'voice', 'location':
    #    must then contain a 'media' field
    # 'messages' field:
    #  -> [Message, ...]: forwarded messages or search result
    # 'telegrambot' field:
    #  -> {}: Telegram bot specified options
    #   - 'disable_web_page_preview': (Boolean, Optional) Disables link previews
    #     for links in this message
    #   - 'disable_notification': (Boolean, Optional) Sends the message silently.
    #     iOS users will not receive a notification, Android users will receive a
    #     notification with no sound. Other apps coming soon.
    #   - 'reply_to_message_id': (Integer, Optional) If the message is a reply,
    #     ID of the original message
    #     Overrides original value.
    #   - 'reply_markup': (ReplyKeyboardMarkup or ReplyKeyboardHide or ForceReply,
    #     Optional) Additional interface options. A JSON-serialized object for a
    #     custom reply keyboard, instructions to hide keyboard or to force a reply
    #     from the user.
    # 'media' field:
    #  -> {}: Media type specified options
    #   - '_file': local path
    #   - 'caption', 'duration', 'performer', 'title', 'width', 'height',
    #     'latitude', 'longitude': media specified options in Telegram Bot API
    # 'alttext' field -> str: alternative text, for media types
    'reply' # Replied message: Message
))

class Logger:
    def log(self, msg):
        pass

    def update_user(self, user):
        pass

    def commit(self):
        pass

    def close(self):
        pass

class Protocol:
    def __init__(self, config, bus):
        self.config = config
        self.bus = bus

    def start_polling(self):
        pass

    def send(self, response, protocol):
        # -> Message
        pass

    def forward(self, msg, protocol):
        # -> Message
        pass

    def status(self, dest, action):
        '''
        Protocol-specified status.
        Telegram Bot API:
        'typing' for text messages,
        'upload_photo' for photos,
        'record_video' or 'upload_video' for videos,
        'record_audio' or 'upload_audio' for audio files,
        'upload_document' for general files,
        'find_location' for location data.
        Other protocols may implement above status.
        `action` may also be: 'online', 'offline'
        '''
        pass

    def close(self):
        pass
