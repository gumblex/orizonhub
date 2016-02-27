#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import hashlib

import requests

class BasePasteBin:
    pass

class FilePasteBin(BasePasteBin):
    def paste(self, data=None, filename=None):
        raise NotImplementedError

class TextPasteBin(BasePasteBin):
    def paste(self, text, title=None):
        raise NotImplementedError

class SelfHostedTxtSore(FilePasteBin):
    def paste(self, text, title=None):
        ...
