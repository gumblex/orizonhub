#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging


from . import base
from .config import config

bot = base.BotInstance(config)
