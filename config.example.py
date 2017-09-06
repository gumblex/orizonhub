#!/usr/bin/env python3
# -*- coding: utf-8 -*-

config = {
    # the classical --verbose switch
    'debug': True,
    # status file
    # for example can record the last Telegram API offset
    # filename (in JSON format) or ':SQLite3:'
    'status': ':SQLite3:',
    # is appeard in /help message
    'bot_fullname': 'Mr. Some Bot',
    # should be \w+
    'bot_nickname': 'SomeBot',
    # the canonical name of your group (not important)
    'group_name': '##Orz',
    # the timezone used in displaying history-related command result
    'timezone': 'Asia/Shanghai',
    # for API (currently not used)
    'secretkey': 'SECRET_KEY',
    # config for individual commands
    'command_config': {
        'autoclose': False,
        # whether the bot should send a welcome message when a user joined the group
        'welcome': True
    },
    # can have SQLite3 and Plain Text formats
    'loggers': {
        'sqlite': 'chatlogv2.db',
        'textlog': 'chatlog.txt'
    },
    # which of the following protocols should be mainly relied on
    # mainly for logging bot messages
    'main_protocol': 'telegrambot',
    'protocols': {
        'irc': {
            # basic things
            'server': 'chat.freenode.net',
            'port': 6697,
            'ssl': True,
            'username': 'NotOrizon',
            'ident': 'NotOrizon',
            'realname': 'NotOrizon Bot',
            # 'password': 'something',
            'channel': '##Orz',
            # can ignore some bots when relaying messages
            # None or regex
            'ignored_user': None,
            # if usernames in forwarded messages should be colored
            'colored': False,
            # if we should include an excerpt of the replied message
            # like: [alice] Re bob:「we have a…」ok got it
            'long_reply': False,
            # other relay bots in IRC, be properly formatted when relayed again
            # read only
            'proxies': [
                # protocol, relay bot nick regex, regex: (nick) (message)
                # other messages sent by this user are considered service message
                ('xmpp', '^OrzGTalk.*', r'\(GTalk\) (\w+): (.+)$'),
                ('tox', '^OrzTox.*', r'\((.+)\) (.+)$'),
                ('irc2p', '^OrzI2P.*', r'\[(.+)\] (.+)$'),
            ]
        },
        'telegrambot': {
            # your API token
            'token': '123456789:AbCdEf_1234567890ABCDEFGHIJKLMNOPQR',
            # your group chat id
            # negative as in API response
            'groupid': -1001001023456,
            # bot's Telegram username, not important
            'username': 'notorzdigbot',
            # can ignore some users when relaying messages
            # None or list of ids like [123, 456]
            'ignored_user': None,
        },
        'telegramcli': {
            # optional 'enabled' field for all protocols, default True
            'enabled': False,
            # group id, in a tg-cli supported format
            'peername': 'channel#id1001023456',
            # tg-cli executable binary
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
    # forward messages between these protocols
    'forward': ['irc', 'telegrambot', 'http', 'skype'],
    'services': {
        # if has 'pastebin', where we should store files, especially for
        # 'self' hosting type
        'cachepath': 'server/img',
        # can be None, 'self', 'vim-cn'
        # 'self' means you can run a web server serving the contents of the 'cachepath'
        # 'vim-cn' uses the http://img.vim-cn.com/ pastebin
        'pastebin': 'self',
        # max file size for caching
        'maxsize': 4194304,
        # for 'self' hosting, the url prefix
        # for example: https://app.example.com/img/AgADBQ.jpg
        'mediaurl': 'https://app.example.com/img/'
    }
}
