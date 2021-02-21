"""Classes to parse command line arguments.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Any, Dict
from dataclasses import dataclass, field
import logging
import sys
from pathlib import Path
from io import TextIOBase
from optparse import OptionParser
from zensols.persist import persisted
from zensols.config import Dictable
from . import (
    OptionMetaData, PositionalMetaData, ActionMetaData,
    ActionCliError, UsageWriter,
)

logger = logging.getLogger(__name__)


class ActionOptionParser(OptionParser):
    """Implements a human readable implementation of print_help for action based
    command line handlers.

    **Implementation note**: we have to extend :class:`~optparser.OptionParser`
    since the ``-h`` option invokes the print help behavior and then exists.

    """
    def __init__(self, actions: Tuple[ActionMetaData], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usage_writer = UsageWriter(self, actions)

    def print_help(self, file=sys.stdout):
        super().print_help(file)
        self.usage_writer.write(writer=file)


@dataclass
class Action(Dictable):
    """The output of the :class:`.CommandLineParser`.

    """
    meta_data: ActionMetaData = field()
    """The action parsed from the command line."""

    options: Dict[str, Any] = field()
    """The options given as switches."""

    positional: Tuple[str] = field()
    """The positional arguments parsed."""


@dataclass
class CommandLineParser(Dictable):
    actions: Tuple[ActionMetaData]
    top_options: Tuple[OptionMetaData] = field(default_factory=lambda: [])
    version: str = field(default='v0')

    def __post_init__(self):
        if len(self.actions) == 0:
            raise ValueError('must create parser with at least one action')

    def _create_parser(self, actions: Tuple[ActionMetaData]) -> OptionParser:
        return ActionOptionParser(
            actions, version='%prog ' + str(self.version))

    def _configure_parser(self, parser: OptionParser,
                          options: List[OptionMetaData]):
        for opt in options:
            op_opt = opt.create_option()
            parser.add_option(op_opt)

    @persisted('_parser')
    def _get_parser(self) -> ActionOptionParser:
        opts = list(self.top_options)
        actions = self.actions
        if len(self.actions) == 1:
            # TODO: add singleton action doc
            opts.extend(actions[0].options)
            actions = (self.actions[0],)
        parser = self._create_parser(actions)
        self._configure_parser(parser, opts)
        return parser

    @property
    @persisted('_actions')
    def actions_by_name(self) -> Dict[str, ActionMetaData]:
        return {a.name: a for a in self.actions}

    def write_help(self, writer: TextIOBase = sys.stdout):
        self._get_parser().print_help(file=writer)

    def _parse_positional(self, metas: List[PositionalMetaData],
                          vals: List[str]) -> Tuple[Any]:
        def parse(s: str, t: type) -> Any:
            if not isinstance(s, (str, int, bool, Path)):
                raise ValueError(f'unknown parse type: {s}: {t}')
            return t(s)
        return tuple(map(parse, zip(metas, vals)))

    def parse(self, args: List[str]) -> Action:
        parser: OptionParser = self._get_parser()
        (options, args) = parser.parse_args(args)
        if len(self.actions) == 1:
            action_name = self.actions[0].name
        elif len(args) == 0:
            raise ActionCliError('no action given')
        else:
            action_name = args[0]
            args = args[1:]
        action = self.actions_by_name.get(action_name)
        if action is None:
            raise ActionCliError(f'no such action: {action_name}')
        if len(action.positional) != len(args):
            raise ActionCliError(
                f'action {action.name} expects {len(action.arguments)} ' +
                f'but got {len(args)}')
        pargs = self._parse_positional(action.positional, args)
        options = vars(options)
        return Action(action, options, pargs)
