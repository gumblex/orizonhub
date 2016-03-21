#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import sqlite3
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))

from orizonhub import logger

DEST = None
FILENAME_IN = 'chatlog.db'
FILENAME_OUT = 'chatlogv2.db'

if len(sys.argv) > 1:
    DEST = int(sys.argv[1])
else:
    DEST = int(input('Enter group id (negative): '))
if len(sys.argv) > 2:
    FILENAME_IN = sys.argv[2]
if len(sys.argv) > 3:
    FILENAME_OUT = sys.argv[3]

if not os.path.isfile(FILENAME_IN):
    print('Database file not found.')
    sys.exit(1)

DB_IN = sqlite3.connect(FILENAME_IN)
CUR_IN = DB_IN.cursor()

print('Importing:')
dest = logger.SQLiteLogger(FILENAME_OUT)
user_index = {}
irc_user_index = {}

print('* users')
CUR = dest.conn.cursor()
for pid, username, first_name, last_name in CUR_IN.execute('SELECT id, username, first_name, last_name FROM users'):
    user = dest.update_user(User(
        None, 'telegram', 1, pid, username, first_name, last_name, None), CUR)
    assert user.id
    user_index[pid] = user
print('* messages')
for mid, src, text, media, date, fwd_src, fwd_date, reply_id in conn.execute('SELECT id, src, text, media, date, fwd_src, fwd_date, reply_id FROM messages ORDER BY date ASC, id ASC'):
    if mid < 0:
        media_obj = json.loads(media or '{}')
        src = dest.update_user(User(None, protocol, UserType.user, None,
            nick, realname, None, nick.rstrip('_')), CUR)
    # TODO: IRC proxied protocol

DB.commit()
print('Done.')
