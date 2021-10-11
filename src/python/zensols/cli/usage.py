from __future__ import annotations
"""Utility classes to write command line help.

"""
__author__ = 'Paul Landes'

from typing import Tuple
from dataclasses import dataclass, field
import logging
import sys
from io import TextIOBase
from optparse import OptionParser, Option
from zensols.config import Writable
from . import OptionMetaData, ActionMetaData

logger = logging.getLogger(__name__)


class UsageActionOptionParser(OptionParser):
    """Implements a human readable implementation of :meth:`print_help` for action
    based command line handlers.

    **Implementation note**: we have to extend :class:`~optparser.OptionParser`
    since the ``-h`` option invokes the print help behavior and then exists
    printing the second pass action options.  Instead, we look for the help
    option in the first pass, print help with the correction options, then
    exit.

    """
    def __init__(self, actions: Tuple[ActionMetaData], doc: str = None,
                 default_action: str = None, *args, **kwargs):
        super().__init__(*args, add_help_option=False, **kwargs)
        self.usage_writer = UsageWriter(self, actions, doc, default_action)
        self.add_option(self._create_help())

    def _create_help(self):
        return Option('--help', '-h',
                      help='show this help message and exit',
                      action='store_true')

    def print_help(self, file: TextIOBase = sys.stdout,
                   include_actions: bool = True):
        super().print_help(file)
        if include_actions:
            self.usage_writer.write(writer=file)


@dataclass
class _Formatter(Writable):
    def _write_two_col(self, a: str, b: str, width: int, depth: int = 0,
                       writer: TextIOBase = sys.stdout):
        fmt = '{:<' + str(width) + '}{}'
        s = fmt.format(a, b)
        self._write_line(s, depth, writer)

    def _write_three_col(self, a: str, b: str, c: str, w1: int, w2: int,
                         depth: int = 0, writer: TextIOBase = sys.stdout):
        fmt = '{:<' + str(w1) + '}{:<' + str(w2) + '}{}'
        #print('F', fmt)
        s = fmt.format(a, b, c)
        self._write_line(s, depth, writer)


@dataclass
class _OptFormatter(_Formatter):
    action: _ActionFormatter
    opt: OptionMetaData

    def __post_init__(self):
        opt = self.opt
        opt_left_space = ' ' * self.action.parent.opt_left_space
        sep = '' if opt.short_name is None else ', '
        long_opt = opt.long_option
        short_opt = '' if opt.short_option is None else opt.short_option
        metavar = '' if opt.metavar is None else f' {opt.metavar}'
        self.opt_str = f'{opt_left_space}{short_opt}{sep}{long_opt}{metavar}'

    @property
    def parent(self) -> UsageWriter:
        return self.action.parent

    @property
    def doc(self) -> str:
        return '' if self.opt.doc is None else self.opt.doc

    @property
    def default(self) -> str:
        if self.opt.default is not None and self.opt.dtype != bool:
            return self.opt.default_str
        else:
            return ''

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        w1 = self.parent.two_col_width
        w2 = self.parent.three_col_width
        self._write_three_col(self.opt_str, self.default, self.doc,
                              w1, w2, depth, writer)


@dataclass
class _ActionFormatter(_Formatter):
    parent: UsageWriter
    action: ActionMetaData
    action_name: str = field(default=None)
    opts: Tuple[_OptFormatter] = field(default=None)

    def __post_init__(self):
        action = self.action
        if len(action.positional) == 0:
            args = ''
        else:
            pargs = ', '.join(map(lambda p: p.name, action.positional))
            args = f' <{pargs}>'
        self.action_name = action.name + args
        if self.parent.default_action == self.action_name:
            self.action_name = f'{self.action_name} (default)'
        self.opts = tuple(map(lambda of: _OptFormatter(self, of),
                              action.options))

    @property
    def opt_str_len(self) -> int:
        return max(len(o.opt_str) for o in self.opts)

    @property
    def def_str_len(self) -> int:
        return max(len(o.default) for o in self.opts)

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        w1 = self.parent.two_col_width
        w2 = self.parent.three_col_width
        self._write_three_col(self.action_name, '', self.action.doc, w1, w2,
                              depth, writer)
        for opt in self.opts:
            self._write_object(opt, depth, writer)


@dataclass
class UsageWriter(Writable):
    """Generates the usage and help messages for an :class:`optparse.OptionParser`.

    """
    parser: OptionParser = field()
    """Parses the command line in to primitive Python data structures."""

    actions: Tuple[ActionMetaData] = field()
    """The set of actions to document as a usage."""

    doc: str = None
    """The application document string."""

    default_action: str = field(default=None)
    """The default mnemonic use when the user does not supply one."""

    sort_actions: bool = field(default=False)
    """If ``True`` sort mnemonic output."""

    opt_left_space: int = field(default=2)
    inter_col_space: int = field(default=5)

    @property
    def two_col_width(self) -> int:
        return max(a.opt_str_len for a in self.action_formatters) + \
            self.inter_col_space

    @property
    def three_col_width(self) -> int:
        return max(a.def_str_len for a in self.action_formatters) + \
            self.inter_col_space
#            self.two_col_width

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        self.writeX(depth, writer)
        if self.sort_actions:
            actions = sorted(self.actions, key=lambda a: a.name)
        else:
            actions = self.actions
        # format text for each action and respective options
        action: ActionMetaData
        formatters = tuple(map(lambda a: _ActionFormatter(self, a), actions))
        fmt_len = len(formatters)
        if fmt_len > 1:
            writer.write('\nActions:\n')
        for i, fmt in enumerate(formatters):
            self._write_object(fmt, depth, writer)
            if i < fmt_len - 1:
                self._write_empty(writer)

    def writeX(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        if self.sort_actions:
            actions = sorted(self.actions, key=lambda a: a.name)
        else:
            actions = self.actions
        action_help = []
        opt_str_len = 0
        def_str_len = 0
        action_name_len = 0

        # format text for each action and respective options
        action: ActionMetaData
        for action in actions:
            action_doc = action.doc or ''
            opt_strs = []
            if len(action.positional) == 0:
                args = ''
            else:
                pargs = ', '.join(map(lambda p: p.name, action.positional))
                args = f' <{pargs}>'
            action_name = action.name + args
            if self.default_action == action_name:
                action_name = f'{action_name} (default)'
            action_name_len = max(action_name_len, len(action_name))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'options for {action.name}: {action.options}')
            opt: OptionMetaData
            for opt in action.options:
                sep = '' if opt.short_name is None else ', '
                if opt.default is not None and opt.dtype != bool:
                    default = opt.default_str
                else:
                    default = ''
                long_opt = opt.long_option
                short_opt = '' if opt.short_option is None else opt.short_option
                metavar = '' if opt.metavar is None else f' {opt.metavar}'
                doc = '' if opt.doc is None else opt.doc
                opt_str = f'  {short_opt}{sep}{long_opt}{metavar}'
                opt_strs.append({'str': opt_str,
                                 'default': default,
                                 'help': doc})
                opt_str_len = max(opt_str_len, len(opt_str))
                def_str_len = max(def_str_len, len(default))
            action_help.append(
                {'name': action_name,
                 'doc': action_doc,
                 'opts': opt_strs})

        action_fmt_str = '{:<' + str(action_name_len + 3) + '}  {}'
        opt_str_fmt = ('{:<' + str(opt_str_len) + '}  {:<' +
                       str(def_str_len) + '}  {}\n')
        print('O', opt_str_fmt)

        if len(self.actions) > 1:
            writer.write('\nActions:\n')
            for i, ah in enumerate(action_help):
                aline = action_fmt_str.format(ah['name'], ah['doc'])
                writer.write(aline + '\n')
                for op in ah['opts']:
                    writer.write(opt_str_fmt.format(
                        op['str'], op['default'], op['help']))
                if i < len(action_help) - 1:
                    writer.write('\n')

    def __post_init__(self):
        if self.sort_actions:
            self.actions = sorted(self.actions, key=lambda a: a.name)
        self.action_names = tuple(map(lambda a: a.name, self.actions))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'actions: {self.action_names}')
        if len(self.action_names) > 1:
            names = '|'.join(self.action_names)
            if self.default_action is None:
                opts = f"<{names}> "
            else:
                opts = f"[{names}] "
        elif len(self.action_names) > 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'action: {self.actions[0]}')
            opts = ', '.join(map(lambda p: p.name, self.actions[0].positional))
            if len(opts) > 0:
                opts = f'<{opts}> '
        else:
            opts = ''
        if self.doc is None:
            doc = ''
        else:
            doc = f'\n\n{self.doc}'
        self.parser.usage = f"%prog {opts}[options]:{doc}"

        # ------------------------------
        if self.sort_actions:
            actions = sorted(self.actions, key=lambda a: a.name)
        else:
            actions = self.actions
        # format text for each action and respective options
        action: ActionMetaData
        self.action_formatters = tuple(
            map(lambda a: _ActionFormatter(self, a), actions))
