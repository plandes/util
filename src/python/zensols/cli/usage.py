"""Utility classes to write command line help.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Tuple, Iterable, List, Union, Optional, Sequence
from dataclasses import dataclass, field
import logging
import os
import sys
import re
from itertools import chain
from pathlib import Path
from io import TextIOBase
from optparse import OptionParser
from zensols.config import Writable, Dictable
from zensols.persist import persisted
from . import OptionMetaData, ActionMetaData, PositionalMetaData

logger = logging.getLogger(__name__)


@dataclass
class UsageConfig(Dictable):
    """Configuraiton information for the command line help.

    """
    width: int = field(default=None)
    """The max width to print help."""

    max_first_col: Union[float, int] = field(default=0.4)
    """Maximum width of the first column.  If this is a float, then it is computed
    as a percentage of the terminal width.

    """
    max_metavar_len: Union[float, int] = field(default=0.15)
    """Max length of the option type."""

    max_default_len: Union[float, int] = field(default=0.1)
    """Max length in characters of the default value."""

    left_indent: int = field(default=2)
    """The number of left spaces for the option and positional arguments."""

    inter_col_space: int = field(default=2)
    """The number of spaces between all three columns."""

    sort_actions: bool = field(default=False)
    """If ``True`` sort mnemonic output."""

    def __post_init__(self):
        if self.width is None:
            try:
                self.width = os.get_terminal_size()[0]
            except OSError as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'can not get terminal size: {e}')
                self.width = 0
        if self.width == 0:
            self.width = 80
        if self.max_first_col is None:
            self.max_first_col = 0.4
        if isinstance(self.max_first_col, float):
            self.max_first_col = int(self.width * self.max_first_col)
        if isinstance(self.max_metavar_len, float):
            self.max_metavar_len = int(self.width * self.max_metavar_len)
        if isinstance(self.max_default_len, float):
            self.max_default_len = int(self.width * self.max_default_len)


class UsageActionOptionParser(OptionParser):
    """Implements a human readable implementation of :meth:`print_help` for action
    based command line handlers.

    **Implementation note**: we have to extend :class:`~optparser.OptionParser`
    since the ``-h`` option invokes the print help behavior and then exists
    printing the second pass action options.  Instead, we look for the help
    option in the first pass, print help with the correction options, then
    exit.

    """
    def __init__(self, actions: Tuple[ActionMetaData, ...],
                 options: Tuple[OptionMetaData, ...], usage_config: UsageConfig,
                 doc: str = None, default_action: str = None, *args, **kwargs):
        super().__init__(*args, add_help_option=False, **kwargs)
        help_op = OptionMetaData(
            'help', 'h',
            metavar='[actions]',
            dtype=bool,
            doc='show this help message and exit')
        version_op = OptionMetaData(
            'version', None, dtype=bool,
            doc='show the program version and exit')
        options = [help_op, version_op] + list(options)
        self._usage_writer = _UsageWriter(
            self, actions, options, doc, usage_config, default_action)
        self.add_option(help_op.create_option())

    def print_help(self, file: TextIOBase = sys.stdout,
                   include_actions: bool = True,
                   action_metas: Sequence[ActionMetaData] = None):
        """Write the usage information and help text.

        :param include_actions: if ``True`` write each actions' usage as well

        :param actions: the list of actions to output, or ``None`` for all

        """
        self._usage_writer.write(
            writer=file,
            include_actions=include_actions,
            action_metas=action_metas)


@dataclass
class _Formatter(Writable):
    """A formattingn base class that has utility methods.

    """
    _BACKTICKS_REGEX = re.compile(r"``([^`]+)``")

    def _format_doc(self, doc: str = None) -> str:
        doc = '' if doc is None else doc
        doc = re.sub(self._BACKTICKS_REGEX, r'"\1"', doc)
        return doc

    def _write_three_col(self, a: str, b: str, c: str, depth: int = 0,
                         writer: TextIOBase = sys.stdout):
        a = '' if a is None else a
        b = '' if b is None else b
        c = '' if c is None else c
        w1 = self.usage_formatter.two_col_width
        w2 = self.usage_formatter.three_col_width
        a = self._trunc(a, self.usage_formatter.max_first_col)
        fmt = '{:<' + str(w1) + '}{:<' + str(w2) + '}{}'
        s = fmt.format(a, b, c)
        sp = self._get_str_space(w1 + w2)
        self._write_wrap(s, depth, writer, subsequent_indent=sp)


@dataclass
class _OptionFormatter(_Formatter):
    """Write the option, which includes the option name and documenation.

    """
    usage_formatter: _UsageWriter
    opt: OptionMetaData
    usage_config: UsageConfig

    def __post_init__(self):
        self.WRITABLE_MAX_COL = self.usage_config.width
        opt = self.opt
        self.doc = self._format_doc(self.opt.doc)
        left_indent: str = ' ' * self.usage_config.left_indent
        max_olen: int = self.usage_config.max_metavar_len
        sep: str = '' if opt.short_name is None else ', '
        long_opt: str = opt.long_option
        short_opt: str = '' if opt.short_option is None else opt.short_option
        metavar: str = '' if opt.metavar is None else opt.metavar
        mlen, over = self._get_min_default_len()
        self._opt_str = f'{left_indent}{short_opt}{sep}{long_opt}'
        if len(metavar) > max_olen:
            if metavar.find('|') > -1:
                metavar = metavar[1:-1]
                if len(self.doc) > 0:
                    self.doc += ', '
                self.doc += f"X is one of: {', '.join(metavar.split('|'))}"
                self._opt_str += ' X'
            else:
                if len(self.doc) > 0:
                    self.doc += ', of '
                self.doc += f'type {metavar}'
        else:
            self._opt_str += f' {metavar}'
        if over:
            self.doc += f' with default {self.opt.default_str}'

    def _get_min_default_len(self) -> Tuple[Optional[int], bool]:
        mdlen: int = None
        over: bool = False
        if self.opt.default is not None and self.opt.dtype != bool:
            mdlen: int = self.usage_config.max_default_len
            over = (len(self.opt.default_str) + 3) > mdlen
        return mdlen, over

    @property
    def default(self) -> str:
        mlen, over = self._get_min_default_len()
        if mlen is not None:
            s: str = self.opt.default_str
            if over:
                s = s[:mlen] + '...'
            return s
        else:
            return ''

    def add_first_col_width(self, widths: List[int]):
        widths.append(len(self._opt_str))

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        self._write_three_col(
            self._opt_str, self.default, self.doc, depth, writer)


@dataclass
class _PositionalFormatter(_Formatter):
    usage_formatter: _UsageFormatter
    pos: PositionalMetaData

    def __post_init__(self):
        self.WRITABLE_MAX_COL = self.usage_formatter.usage_config.width
        spl = self.usage_formatter.writer.usage_config.left_indent
        sp = self._get_str_space(spl)
        mv = ''
        if self.pos.metavar is not None:
            mv = f' {self.pos.metavar}'
        self.name = f'{sp}{self.pos.name}{mv}'
        self.doc = self._format_doc(self.pos.doc)

    def add_first_col_width(self, widths: List[int]):
        widths.append(len(self.name))

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        self._write_three_col(self.name, '', self.doc, depth, writer)


@dataclass
class _ActionFormatter(_Formatter):
    """Write the action, which includes the name, positional arguments, and
    documentation in one line, then the options afterward.

    """
    usage_formatter: _UsageFormatter
    action: ActionMetaData
    usage_config: UsageConfig = field()
    action_name: str = field(default=None)
    opts: Tuple[_OptionFormatter] = field(default=None)
    pos: Tuple[_PositionalFormatter] = field(default=None)

    def __post_init__(self):
        self.WRITABLE_MAX_COL = self.usage_config.width
        action = self.action
        if len(action.positional) == 0:
            args = ''
        else:
            pargs = ', '.join(map(lambda p: p.name, action.positional))
            args = f' <{pargs}>'
        self.action_name = action.name + args
        if self.usage_formatter.default_action == self.action_name:
            self.action_name = f'{self.action_name} (default)'
        self.opts = tuple(map(
            lambda of: _OptionFormatter(
                self.usage_formatter, of, self.usage_config),
            action.options))
        self.pos = tuple(map(
            lambda pos: _PositionalFormatter(self.usage_formatter, pos),
            action.positional))
        self.doc = self._format_doc(self.action.doc)

    def add_first_col_width(self, widths: List[int]):
        widths.append(len(self.action_name))
        for of in self.opts:
            of.add_first_col_width(widths)
        for pos in self.pos:
            pos.add_first_col_width(widths)

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        self._write_three_col(
            self.action_name, '', self.doc, depth, writer)
        for pos in self.pos:
            self._write_object(pos, depth, writer)
        for opt in self.opts:
            self._write_object(opt, depth, writer)


@dataclass
class _UsageFormatter(_Formatter):
    """Write the global options and all actions.

    """
    writer: _UsageWriter
    actions: Tuple[ActionMetaData, ...]
    usage_config: UsageConfig
    global_options: Tuple[OptionMetaData, ...]
    glob_option_formatters: List[_OptionFormatter] = field(default=None)
    action_formatters: List[_ActionFormatter] = field(default=None)
    pos_formatters: List[_PositionalFormatter] = field(default=None)

    def __post_init__(self):
        self.WRITABLE_MAX_COL = self.usage_config.width
        self.glob_option_formatters = list(
            map(lambda o: _OptionFormatter(self, o, self.usage_config),
                self.global_options))
        self.action_formatters = list(
            map(lambda a: _ActionFormatter(self, a, self.usage_config),
                self.actions))
        self.pos_formatters = []
        if self.is_singleton_action:
            for af in self.action_formatters:
                self.glob_option_formatters.extend(af.opts)
                self.pos_formatters.extend(af.pos)
            self.action_formatters.clear()

    @property
    def is_singleton_action(self) -> bool:
        return len(self.actions) == 1

    @property
    def default_action(self):
        return self.writer.default_action

    @property
    def max_first_col(self) -> int:
        return self.writer.usage_config.max_first_col

    def _get_opt_formatters(self) -> Iterable[_OptionFormatter]:
        return chain.from_iterable(
            [chain.from_iterable(
                map(lambda f: f.opts, self.action_formatters)),
             self.glob_option_formatters])

    @property
    @persisted('_two_col_width_pw')
    def two_col_width(self) -> int:
        widths = []
        for af in self.action_formatters:
            af.add_first_col_width(widths)
        for go in self.glob_option_formatters:
            go.add_first_col_width(widths)
        for po in self.pos_formatters:
            po.add_first_col_width(widths)
        return max(widths) + self.usage_config.inter_col_space

    @property
    @persisted('_three_col_width_pw')
    def three_col_width(self) -> int:
        return max(len(a.default) for a in self._get_opt_formatters()) + \
            self.usage_config.inter_col_space

    def get_option_usage_names(self, expand: bool = True) -> str:
        actions: Iterable[Action] = filter(
            lambda a: a.is_usage_visible, self.actions)
        action_names: Tuple[str, ...] = tuple(map(lambda a: a.name, actions))
        if len(action_names) > 1:
            if expand:
                names = '|'.join(action_names)
            else:
                names = 'actions'
            if self.default_action is None:
                opts = f"<{names}> "
            else:
                opts = f"[{names}] "
        elif len(action_names) > 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'action: {self.actions[0]}')
            opts = ', '.join(map(lambda p: p.name, self.actions[0].positional))
            if len(opts) > 0:
                opts = f'<{opts}> '
        else:
            opts = ''
        return opts

    def _write_options(self, depth: int, writer: TextIOBase) -> bool:
        n_fmt = len(self.glob_option_formatters)
        has_opts = n_fmt > 0
        if has_opts:
            self._write_line('Options:', depth, writer)
            for i, of in enumerate(self.glob_option_formatters):
                of.write(depth, writer)
        return has_opts

    def _write_actions(self, depth: int, writer: TextIOBase,
                       action_metas: Sequence[ActionMetaData] = None):
        am_set: Set[str] = None
        if action_metas is not None:
            am_set = set(map(lambda a: a.name, action_metas))
        # get only visible actions
        fmts: Tuple[_ActionFormatter] = tuple(filter(
            lambda f: f.action.is_usage_visible and \
                (am_set is None or f.action.name in am_set),
            self.action_formatters))
        n_fmt: int = len(fmts)
        if n_fmt > 0:
            self._write_line('Actions:', depth, writer)
        i: int
        fmt: _ActionFormatter
        for i, fmt in enumerate(fmts):
            am: ActionMetaData = fmt.action
            self._write_object(fmt, depth, writer)
            if i < n_fmt - 1:
                self._write_empty(writer)

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout,
              include_singleton_positional: bool = True,
              include_options: bool = True,
              include_actions: bool = True,
              action_metas: Sequence[ActionMetaData] = None):
        if self.is_singleton_action and include_singleton_positional and \
           len(self.pos_formatters) > 0:
            self._write_line('Positional:', depth, writer)
            for po in self.pos_formatters:
                self._write_object(po, depth, writer)
            if include_options or include_actions:
                self._write_empty(writer)
        if include_options:
            if self._write_options(depth, writer) and include_actions and \
               len(self.action_formatters) > 0:
                self._write_empty(writer)
        if include_actions:
            self._write_actions(depth, writer, action_metas)


@dataclass
class _UsageWriter(_Formatter):
    """Generates the usage and help messages for an :class:`optparse.OptionParser`.

    """
    parser: OptionParser = field()
    """Parses the command line in to primitive Python data structures."""

    actions: Tuple[ActionMetaData, ...] = field()
    """The set of actions to document as a usage."""

    global_options: Tuple[OptionMetaData, ...] = field()
    """Application level options (i.e. level, config, verbose etc)."""

    doc: str = field()
    """The application document string."""

    usage_config: UsageConfig = field(default_factory=UsageConfig)
    """Configuraiton information for the command line help."""

    default_action: str = field(default=None)
    """The default mnemonic use when the user does not supply one."""

    usage_formatter: _UsageFormatter = field(default=None)
    """The usage formatter used to generate the documentation."""

    def __post_init__(self):
        self.WRITABLE_MAX_COL = self.usage_config.width
        if self.usage_config.sort_actions:
            actions = sorted(self.actions, key=lambda a: a.name)
        else:
            actions = self.actions
        self.usage_formatter = _UsageFormatter(
            self, actions, self.usage_config, self.global_options)

    def get_prog_usage(self) -> str:
        opt_usage: str = '[options]:'
        prog: str = '<python>'
        if len(sys.argv) > 0:
            prog_path: Path = Path(sys.argv[0])
            prog = prog_path.name
        opts = self.usage_formatter.get_option_usage_names()
        usage = f'{prog} {opts}{opt_usage}'
        if len(usage) > (self.usage_config.width - len(opt_usage)):
            opts = self.usage_formatter.get_option_usage_names(expand=False)
            usage = f'{prog} {opts}{opt_usage}'
        return usage

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout,
              include_singleton_positional: bool = True,
              include_options: bool = True,
              include_actions: bool = True,
              action_metas: Sequence[ActionMetaData] = None):
        prog = self.get_prog_usage()
        # if user specified help action(s) on the command line, only print the
        # action(s)
        if action_metas is None:
            self._write_line(f'Usage: {prog}', depth, writer)
            self._write_empty(writer)
            if self.doc is not None:
                doc = self._format_doc(self.doc)
                self._write_wrap(doc, depth, writer)
                self._write_empty(writer)
        else:
            include_options = False
        self.usage_formatter.write(
            depth, writer,
            include_singleton_positional=include_singleton_positional,
            include_options=include_options,
            include_actions=include_actions,
            action_metas=action_metas)
