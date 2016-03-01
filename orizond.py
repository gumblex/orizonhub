#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging

from config import config
from orizonhub import base

logging.basicConfig(stream=sys.stderr, format='%(asctime)s [%(levelname)s] %(message)s', level=logging.DEBUG if config['debug'] else logging.INFO)

bot = base.BotInstance(config)

try:
    bot.start()
finally:
    bot.exit()
