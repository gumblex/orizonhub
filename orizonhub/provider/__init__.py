#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from . import command
from .irc import IRCProtocol
from .rawsocket import RawSocketProtocol
from .telegrambot import TelegramBotProtocol
from .telegramcli import TelegramCliProtocol
from .logger import Logger, TextLogger, SQLiteLogger, BasicStateStore, SQLiteStateStore

loggers = {
'sqlite': SQLiteLogger,
'text': TextLogger,
'dummy': Logger
}

protocols = {
'socket': RawSocketProtocol,
'irc': IRCProtocol,
'telegrambot': TelegramBotProtocol,
'telegramcli': TelegramCliProtocol
}

general_handlers = command.general_handlers
commands = command.commands
