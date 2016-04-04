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
