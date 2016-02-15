#!/usr/bin/env python3
# -*- coding: utf-8 -*-

config = {
    'debug': True,
    # status file
    # filename or ':SQLite3:'
    'status': ':SQLite3:',
    'canonical_bot_name': 'SomeBot',
    'canonical_group_name': '##Orz',
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
    'protocols': {
        'irc': {
            'server': 'chat.freenode.net',
            'port': 6697,
            'ssl': True,
            'username': 'NotOrizon',
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
            'servemedia': 'self',
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
            'socketfile': '/tmp/orizon_http.sock',
            # read/write
            'proxies': [
                ('http', 'https://web.example.com/'),
                ('skype', 'https://api.example.com/message/')
            ]
        }
    },
    'forwarders': {
        'in': ['irc', 'telegram', 'http', 'skype'],
        'out': ['irc', 'telegram', 'http', 'skype']
    },
    'services': {
        'mediapath': 'server/img',
        'mediaurl': 'https://app.example.com/img/'
    }
}
