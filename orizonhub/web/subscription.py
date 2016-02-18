#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sqlite3

re_tag = re.compile(r"#\w+", re.UNICODE)

def keyword_filter(msg, kwds):
    return any(k in msg.text for k in msg)

def tag_filter(msg, tags):
    return any(k in msg.text for k in msg)
