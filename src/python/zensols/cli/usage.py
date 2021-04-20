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

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
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
