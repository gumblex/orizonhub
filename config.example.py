#!/usr/bin/env python3
# -*- coding: utf-8 -*-

config = {
    'debug': True,
    # status file
    # filename or ':SQLite3:'
    'status': ':SQLite3:',
    'bot_fullname': 'Mr. Some Bot',
    # should be \w+
    'bot_nickname': 'SomeBot',
    'group_name': '##Orz',
    'timezone': 'Asia/Shanghai',
    'secretkey': 'SECRET_KEY',
    'command_config': {
        'autoclose': False,
        'welcome': True
    },
    'loggers': {
        'sqlite': 'chatlogv2.db',
        'text': 'chatlog.txt'
    },
    # for logging bot messages
    'main_protocol': 'telegrambot',
    'protocols': {
        'irc': {
            'server': 'chat.freenode.net',
            'port': 6697,
            'ssl': True,
            'username': 'NotOrizon',
            # 'password': 'something',
            'channel': '##Orz',
            # None or regex
            'ignore': None,
            # read only
            'proxies': [
                # protocol, relay bot nick regex, regex: (nick) (message)
                # other messages sent by this user are considered service message
                ('xmpp', '^OrzGTalk.*', r'\(GTalk\) (\w+): (.+)$'),
                ('tox', '^OrzTox.*', r'[([^]]+)] (.+)$'),
                ('irc2p', '^OrzI2P.*', r'[([^]]+)] (.+)$')
            ]
        },
        'telegrambot': {
            'token': '123456789:AbCdEf_1234567890ABCDEFGHIJKLMNOPQR',
            # negative as in API response
            'groupid': -1001001023456,
            'username': 'notorzdigbot'
        },
        'telegramcli': {
            # optional 'enabled' field for all protocols, default True
            'enabled': False,
            'peername': 'channel#id1001023456',
            'bin': '../tg/bin/telegram-cli'
        },
        'socket': {
            'enabled': False,
            'address': '/tmp/orizon_http.sock',
            # read/write
            'proxies': [
                ('http', 'https://web.example.com/'),
                ('skype', 'https://api.example.com/message/')
            ]
        }
    },
    'forward': ['irc', 'telegrambot', 'http', 'skype'],
    'services': {
        'cachepath': 'server/img',
        # can be None, 'self', 'vim-cn'
        'pastebin': 'self',
        'maxsize': 4194304,
        # for 'self'
        'mediaurl': 'https://app.example.com/img/'
    }
}
