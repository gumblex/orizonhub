#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import socket

address = ('172.20.1.3', 13332)

dumpsjson = lambda x: json.dumps(x).encode('utf-8')
loadsjson = lambda x: json.loads(x.decode('utf-8'))

def recvall(sock, buf=1024):
    data = sock.recv(buf)
    alldata = [data]
    while data and data[-1] != 10:
        data = sock.recv(buf)
        alldata.append(data)
    return b''.join(alldata)[:-1]


def sendall(sock, data):
    sock.sendall(data + b'\n')


def receive(data, autorestart=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(address)
        sendall(sock, data)
    except (ConnectionRefusedError, BrokenPipeError) as ex:
        raise ex
    received = recvall(sock)
    sock.close()
    return received


def translate(text, mode, withcount=False, withinput=True, align=True):
    return loadsjson(receive(dumpsjson((mode, text, withcount, withinput, align))))


def rawtranslate(text, mode, withcount=False):
    return loadsjson(receive(dumpsjson((mode + '.raw', text))))


def modelname():
    return loadsjson(receive(dumpsjson(('modelname',))))


def cut(*args, **kwargs):
    return loadsjson(receive(dumpsjson(('cut', args, kwargs))))


def cut_for_search(*args, **kwargs):
    return loadsjson(receive(dumpsjson(('cut_for_search', args, kwargs))))


def tokenize(*args, **kwargs):
    return loadsjson(receive(dumpsjson(('tokenize', args, kwargs))))


class jiebazhc:

    @staticmethod
    def cut(*args, **kwargs):
        return loadsjson(receive(dumpsjson(('jiebazhc.cut', args, kwargs))))

    @staticmethod
    def cut_for_search(*args, **kwargs):
        return loadsjson(receive(dumpsjson(('jiebazhc.cut_for_search', args, kwargs))))

    @staticmethod
    def tokenize(*args, **kwargs):
        return loadsjson(receive(dumpsjson(('jiebazhc.tokenize', args, kwargs))))


def add_word(*args, **kwargs):
    receive(dumpsjson(('add_word', args, kwargs)))


def load_userdict(*args):
    receive(dumpsjson(('load_userdict', args)))


def set_dictionary(*args):
    receive(dumpsjson(('set_dictionary', args)))


def stopserver():
    receive(dumpsjson(('stopserver',)), False)


def ping(autorestart=False):
    try:
        result = receive(dumpsjson(('ping',)), autorestart)
        return result == b'pong'
    except Exception:
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stop':
            if ping():
                stopserver()
        elif sys.argv[1] == 'ping':
            if not ping():
                sys.exit(1)
        elif sys.argv[1] == 'c2m':
            if not ping():
                sys.exit(1)
            sys.stdout.write(translate(sys.stdin.read(), 'c2m', 0, 0, 0) + '\n')
        elif sys.argv[1] == 'm2c':
            if not ping():
                sys.exit(1)
            sys.stdout.write(translate(sys.stdin.read(), 'm2c', 0, 0, 0) + '\n')
        elif sys.argv[1] == 'c2m.raw':
            if not ping():
                sys.exit(1)
            sys.stdout.write(translate(sys.stdin.read(), 'c2m.raw') + '\n')
        elif sys.argv[1] == 'm2c.raw':
            if not ping():
                sys.exit(1)
            sys.stdout.write(translate(sys.stdin.read(), 'm2c.raw') + '\n')
        elif sys.argv[1] == 'modelname':
            if not ping():
                sys.exit(1)
            sys.stdout.write((modelname() or '') + '\n')
    else:
        if not ping():
            sys.exit(1)
