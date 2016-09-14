# The MIT License (MIT)
# 
# Copyright (c) 2015 David Wison
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# pip install python-prctl cffi

from __future__ import division

import os
import sys
import signal
import socket
import struct
import marshal
import resource

import cffi
import prctl

import re
import math
import cmath
import itertools

reload(sys)
sys.setdefaultencoding("utf-8")

_ffi = cffi.FFI()
_ffi.cdef('void _exit(int);')
_libc = _ffi.dlopen(None)

def _exit(n=1):
    """Invoke _exit(2) system call."""
    _libc._exit(n)

def read_exact(fp, n):
    buf = ''
    while len(buf) < n:
        buf2 = os.read(fp.fileno(), n)
        if not buf2:
            _exit(233)
        buf += buf2
    return buf2

def write_exact(fp, s):
    done = 0
    while done < len(s):
        written = os.write(fp.fileno(), s[done:])
        if not written:
            _exit(233)
        done += written

class SecureEvalHost(object):
    def __init__(self):
        self.host, self.child = socket.socketpair()
        self.pid = None
        self.child_globals = {"__builtins__": __builtins__}

    def start_child(self):
        assert not self.pid
        self.pid = os.fork()
        if not self.pid:
            self._child_main()
        self.child.close()

    def kill_child(self):
        assert self.pid
        pid, status = os.waitpid(self.pid, os.WNOHANG)
        os.kill(self.pid, signal.SIGKILL)

    def do_eval(self, msg):
        try:
            return {'result': str(eval(msg['body'], self.child_globals, {}))}
        except Exception as ex:
            return {'result': repr(ex)}

    def _child_main(self):
        self.host.close()
        for fd in map(int, os.listdir('/proc/self/fd')):
            if fd != self.child.fileno():
                try:
                    os.close(fd)
                except OSError:
                    pass

        resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
        prctl.set_seccomp(True)
        while True:
            sz, = struct.unpack('>L', read_exact(self.child, 4))
            doc = marshal.loads(read_exact(self.child, sz))
            if doc['cmd'] == 'eval':
                resp = self.do_eval(doc)
            elif doc['cmd'] == 'exit':
                _exit(0)
            goobs = marshal.dumps(resp)
            write_exact(self.child, struct.pack('>L', len(goobs)))
            write_exact(self.child, goobs)

    def eval(self, s):
        msg = marshal.dumps({'cmd': 'eval', 'body': s})
        write_exact(self.host, struct.pack('>L', len(msg)))
        write_exact(self.host, msg)
        sz, = struct.unpack('>L', read_exact(self.host, 4))
        goobs = marshal.loads(read_exact(self.host, sz))
        return goobs['result']


def go():
    sec = SecureEvalHost()
    sec.child_globals.update({'re': re, 'math': math, 'cmath': cmath, 'itertools': itertools})
    sec.start_child()
    try:
        sys.stdout.write(sec.eval(sys.stdin.read()) + '\n')
    finally:
        sec.kill_child()

if __name__ == '__main__':
    go()
