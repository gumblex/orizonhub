#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import hashlib

import requests

imgfmt = frozenset(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'))

def retrieve(url, filename, raisestatus=True):
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    if raisestatus:
        r.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
        f.flush()
    return r.status_code

class BasePasteBin:

    def __init__(self, cachepath, maxsize):
        self.cachepath = cachepath
        self.maxsize = maxsize
        if not os.path.isdir(self.cachepath):
            os.makedirs(self.cachepath)

    def geturl(self, filename):
        raise NotImplementedError

    def getpath(self, filename):
        fpath = os.path.join(self.cachepath, filename)
        if os.path.isfile(fpath):
            return fpath
        else:
            raise FileNotFoundError(fpath)

    def paste_text(self, text, filename=None):
        data = text.encode('utf-8')
        if not filename:
            filename = hashlib.sha1(data).hexdigest() + '.txt'
        return self.paste_data(data, filename)

    def paste_data(self, data, filename=None):
        if len(data) > self.maxsize:
            raise ValueError("data size exceeds maxsize")
        if not filename:
            filename = hashlib.sha1(data).hexdigest() + '.bin'
        with open(os.path.join(self.cachepath, filename), 'wb') as f:
            f.write(data)
        return self.geturl(filename)

    def paste_url(self, url, filename, size=None):
        if size and size > self.maxsize:
            raise ValueError("file size exceeds maxsize")
        fpath = os.path.join(self.cachepath, filename)
        if not self.exists(filename, size):
            retrieve(url, fpath)
        if os.path.getsize(fpath) > self.maxsize:
            self.remove(self, filename)
            raise ValueError("file size exceeds maxsize")
        return self.geturl(filename)

    def exists(self, filename, size=None):
        fpath = os.path.join(self.cachepath, filename)
        return (os.path.isfile(fpath) and
                (size is None or os.path.getsize(fpath) == size))

    def remove(self, filename):
        try:
            os.unlink(os.path.join(self.cachepath, filename))
        except Exception:
            pass

    def close(self):
        pass

class DummyPasteBin(BasePasteBin):
    '''
    Prevents unnecessary writes and downloads.
    '''
    def __init__(self):
        pass

    def paste_text(self, text, filename=None):
        raise NotImplementedError

    def paste_data(self, data, filename=None):
        raise NotImplementedError

    def paste_url(self, url, filename, size=None):
        raise NotImplementedError

    def exists(self, filename, size=None):
        return False

    def remove(self, filename):
        pass

class SimplePasteBin(BasePasteBin):
    def __init__(self, cachepath, maxsize, baseurl, expire=3*86400):
        self.cachepath = cachepath
        self.maxsize = maxsize
        self.baseurl = baseurl
        self.expire = expire
        if not os.path.isdir(self.cachepath):
            os.makedirs(self.cachepath)

    def geturl(self, filename):
        url = os.path.join(self.baseurl, filename)
        fpath = os.path.join(self.cachepath, filename)
        if not os.path.isfile(fpath):
            raise FileNotFoundError(fpath)
        return url

    def close(self):
        for f in os.listdir(self.cachepath):
            if time.time() - self.expire > os.path.getatime(os.path.join(self.cachepath, f)):
                self.remove(f)

class VimCN(BasePasteBin):
    def geturl(self, filename):
        fpath = os.path.join(self.cachepath, filename)
        if os.path.splitext(filename)[1] in imgfmt:
            r = requests.post('http://img.vim-cn.com/', files={'name': open(fpath, 'rb')})
        elif 23 <= os.path.getsize(fpath) <= 64 * 1024:
            r = requests.post('http://p.vim-cn.com/', data={'vimcn': open(fpath, 'rb')})
        else:
            self.remove(filename)
            raise ValueError("file can't be accepted on vim-cn")
        self.remove(filename)
        return r.text.strip()
