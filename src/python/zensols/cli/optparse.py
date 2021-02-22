"""Classes to parse command line arguments.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Any, Dict, Iterable
from dataclasses import dataclass, field
import logging
import sys
from itertools import chain
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


class CommandLineError(ActionCliError):
    pass


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
                          options: Iterable[OptionMetaData]):
        opt_names = set()
        for opt in options:
            if opt.long_name in opt_names:
                raise ValueError(f'duplicate option: {opt.long_name}')
            opt_names.add(opt.long_name)
            op_opt = opt.create_option()
            parser.add_option(op_opt)

    def _get_top_parser(self, add_all_opts: bool) -> ActionOptionParser:
        opts = list(self.top_options)
        actions = self.actions
        if len(self.actions) == 1:
            # TODO: add singleton action doc
            actions = (self.actions[0],)
            opts.extend(actions[0].options)
        elif add_all_opts:
            opts.extend(chain.from_iterable(
                map(lambda a: a.options, self.actions)))
        parser = self._create_parser(actions)
        self._configure_parser(parser, set(opts))
        return parser

    def _get_action_parser(self, action_meta: ActionMetaData) -> \
            ActionOptionParser:
        parser = self._create_parser(self.actions)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"creating parser for action: '{action_meta.name}' " +
                         f'opts: {action_meta.options}')
        self._configure_parser(parser, action_meta.options)
        return parser

    @property
    @persisted('_actions')
    def actions_by_name(self) -> Dict[str, ActionMetaData]:
        return {a.name: a for a in self.actions}

    def write_help(self, writer: TextIOBase = sys.stdout):
        self._get_top_parser(False).print_help(file=writer)

    def _parse_positional(self, metas: List[PositionalMetaData],
                          vals: List[str]) -> Tuple[Any]:
        def parse(s: str, t: type) -> Any:
            if not isinstance(s, (str, int, bool, Path)):
                raise ValueError(f'unknown parse type: {s}: {t}')
            return t(s)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing positional args: {metas} <--> {vals}')
        return tuple(map(lambda x: parse(x[0], x[1].dtype), zip(vals, metas)))

    def parse(self, args: List[str]) -> Action:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing: {args}')
        parser: OptionParser = self._get_top_parser(True)
        (options, op_args) = parser.parse_args(args)
        second_pass = False
        if len(self.actions) == 1:
            action_name = self.actions[0].name
        elif len(args) == 0:
            raise CommandLineError('no action given')
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'first pass: {options}:{op_args}')
            action_name = op_args[0]
            op_args = op_args[1:]
            second_pass = True
        action = self.actions_by_name.get(action_name)
        if action is None:
            raise CommandLineError(f'no such action: {action_name}')
        if len(action.positional) != len(op_args):
            raise CommandLineError(
                f"action '{action.name}' expects {len(action.positional)} " +
                f'arguments but got {len(op_args)}')
        if second_pass:
            parser: OptionParser = self._get_action_parser(action)
            (options, op_args) = parser.parse_args(args)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'second pass: {options}::{op_args}')
            assert(op_args[0] == action.name)
            op_args = op_args[1:]
        pos_args = self._parse_positional(action.positional, op_args)
        options = vars(options)
        return Action(action, options, pos_args)
