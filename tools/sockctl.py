#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
from multiprocessing.connection import SocketClient

# {"type": "message", "async": true, "message": {<Message>}}
# {"type": "message", "async": false, "message": {<Message>}}
# {"type": "request", "request": {<Request>}}

SIMPLE = len(sys.argv) > 2 and sys.argv[2] == '-s'

with SocketClient(sys.argv[1]) as conn:
    for ln in sys.stdin.buffer:
        if SIMPLE:
            conn.send_bytes(json.dumps({"type": "message", "async": False, "message": {'protocol': 'test', 'text': ln.rstrip(b'\n').decode('utf-8')}}).encode('utf-8'))
        else:
            conn.send_bytes(ln)
        print(conn.recv_bytes().decode('utf-8'))
