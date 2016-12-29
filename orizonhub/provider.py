#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from . import command
from .irc import IRCProtocol
from .telegrambot import TelegramBotProtocol
from .telegramcli import TelegramCliProtocol
from .pastebin import DummyPasteBin, SimplePasteBin, Elimage
from .logger import Logger, TextLogger, SQLiteLogger, BasicStateStore, SQLiteStateStore

loggers = {
'sqlite': SQLiteLogger,
'textlog': TextLogger,
'dummylog': Logger
}

protocols = {
'irc': IRCProtocol,
'telegrambot': TelegramBotProtocol,
'telegramcli': TelegramCliProtocol
}

general_handlers = command.general_handlers
commands = command.commands
