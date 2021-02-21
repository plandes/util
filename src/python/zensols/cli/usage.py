"""Utility classes to write command line help.

"""
__author__ = 'Paul Landes'

from typing import Tuple
from dataclasses import dataclass
import logging
import sys
from functools import reduce
from io import TextIOBase
from optparse import OptionParser
from zensols.config import Writable
from . import Option, Action

logger = logging.getLogger(__name__)


@dataclass
class UsageWriter(Writable):
    parser: OptionParser
    actions: Tuple[Action]

    def __post_init__(self):
        self.actions = sorted(self.actions, key=lambda a: a.name)
        self.action_names = tuple(map(lambda a: a.name, self.actions))
        if len(self.action_names) > 1:
            actions = "<{'|'.join(self.action_names)}>"
        else:
            actions = ''
        self.parser.usage = f"%prog {actions}[options]:"

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        actions = sorted(self.actions, key=lambda a: a.name)
        action_name_len = reduce(lambda x, y: max(x, y),
                                 map(lambda x: len(x), self.action_names))
        action_fmt_str = '  {:<' + str(action_name_len) + '}  {}'
        action_help = []
        opt_str_len = 0
        def_str_len = 0

        # format text for each action and respective options
        action: Action
        for action in actions:
            action_name = action.name
            action_doc = action.doc or ''
            opt_strs = []
            opt: Option
            for opt in action.options:
                sep = '' if opt.short_name is None else ', '
                default = '' if opt.default is None else opt.default
                long_opt = f'--{opt.long_name}'
                short_opt = '' if opt.short_name is None else f'-{opt.short_name}'
                metavar = '' if opt.metavar is None else opt.metavar
                doc = '' if opt.doc is None else opt.doc
                opt_str = f'  {short_opt}{sep}{long_opt}{metavar}'
                opt_strs.append({'str': opt_str,
                                 'default': default,
                                 'help': doc})
                opt_str_len = max(opt_str_len, len(opt_str))
                def_str_len = max(def_str_len, len(default))
            action_help.append(
                {'doc': action_fmt_str.format(action_name, action_doc),
                 'opts': opt_strs})

        opt_str_fmt = ('{:<' + str(opt_str_len) + '}  {:<' +
                       str(def_str_len) + '}  {}\n')

        #self.parser.print_help(writer)

        if len(self.actions) > 1:
            writer.write('\nActions:\n')
            for i, ah in enumerate(action_help):
                writer.write(ah['doc'] + '\n')
                for op in ah['opts']:
                    writer.write(opt_str_fmt.format(
                        op['str'], op['default'], op['help']))
                if i < len(action_help) - 1:
                    writer.write('\n')
