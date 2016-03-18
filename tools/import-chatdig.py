#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
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
out = logger.SQLiteLogger(FILENAME_OUT)

print('* users')
...
print('* messages')
...

DB.commit()
print('Done.')
