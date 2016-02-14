#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging


from . import base
from .config import config

logging.basicConfig(stream=sys.stdout, format='%(asctime)s [%(levelname)s] %(message)s', level=loglevel)

bot = base.BotInstance(config)
