#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from . import support

PREFIX = "/'"

commands = support.cp.commands
general_handlers = support.cp.general_handlers
activate = support.cp.activate
close = support.cp.close

from . import simple
from . import msglog
from . import control
from . import nlp
from . import ghandler

