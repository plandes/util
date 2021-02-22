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

    @property
    def name(self) -> str:
        return self.meta_data.name


@dataclass
class ActionSet(Dictable):
    actions: Tuple[Action]

    @property
    def first_pass_actions(self) -> Iterable[Action]:
        return self.actions[0:-1]

    @property
    def second_pass_action(self) -> Action:
        return self.actions[-1]

    @property
    def by_name(self) -> Dict[str, Action]:
        return {a.name: a for a in self.actions}

    def __getitem__(self, name: str) -> Action:
        return self.by_name[name]

    def __iter__(self) -> Iterable[Action]:
        return iter(self.actions)

    def __len__(self) -> int:
        return len(self.actions)


@dataclass
class CommandLineParser(Dictable):
    actions: Tuple[ActionMetaData]
    version: str = field(default='v0')

    def __post_init__(self):
        if len(self.actions) == 0:
            raise ValueError('must create parser with at least one action')

    @property
    @persisted('_first_pass_actions')
    def first_pass_actions(self) -> Tuple[Action]:
        return tuple(filter(lambda a: a.first_pass, self.actions))

    @property
    @persisted('_second_pass_actions')
    def second_pass_actions(self) -> Tuple[Action]:
        return tuple(filter(lambda a: not a.first_pass, self.actions))

    @property
    @persisted('_actions')
    def actions_by_name(self) -> Dict[str, ActionMetaData]:
        return {a.name: a for a in self.actions}

    @property
    @persisted('_first_pass_options')
    def first_pass_options(self) -> Tuple[OptionMetaData]:
        return tuple(chain.from_iterable(
            map(lambda a: a.options, self.first_pass_actions)))

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

    def _get_first_pass_parser(self, add_all_opts: bool) -> ActionOptionParser:
        opts = list(self.first_pass_options)
        sp_actions = self.second_pass_actions
        if len(sp_actions) == 1:
            # TODO: add singleton action doc
            sp_actions = (sp_actions[0],)
            opts.extend(sp_actions[0].options)
        elif add_all_opts:
            opts.extend(chain.from_iterable(
                map(lambda a: a.options, sp_actions)))
        parser = self._create_parser(sp_actions)
        self._configure_parser(parser, set(opts))
        return parser

    def _get_second_pass_parser(self, action_meta: ActionMetaData) -> \
            ActionOptionParser:
        opts = list(self.first_pass_options)
        opts.extend(action_meta.options)
        parser = self._create_parser(self.second_pass_actions)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"creating parser for action: '{action_meta.name}' " +
                         f'opts: {action_meta.options}')
        self._configure_parser(parser, opts)
        return parser

    def write_help(self, writer: TextIOBase = sys.stdout):
        self._get_first_pass_parser(False).print_help(file=writer)

    def _parse_positional(self, metas: List[PositionalMetaData],
                          vals: List[str]) -> Tuple[Any]:
        def parse(s: str, t: type) -> Any:
            if not isinstance(s, (str, int, bool, Path)):
                raise ValueError(f'unknown parse type: {s}: {t}')
            return t(s)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing positional args: {metas} <--> {vals}')
        return tuple(map(lambda x: parse(x[0], x[1].dtype), zip(vals, metas)))

    @property
    @persisted('_first_pass_by_option')
    def first_pass_by_option(self) -> Dict[str, Action]:
        actions = {}
        for action in self.first_pass_actions:
            for k, v in action.options_by_name.items():
                if k in actions:
                    raise ValueError(
                        f"first pass duplicate option in '{action.name}': {k}")
                actions[k] = action
        return actions

    def parse(self, args: List[str]) -> Tuple[Action]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing: {args}')
        # action instances
        actions: List[Action] = []
        fp_opts = set(map(lambda o: o.long_name, self.first_pass_options))
        second_pass = False
        # first fish out the action name (if given) as a positional parameter
        parser: OptionParser = self._get_first_pass_parser(True)
        (options, op_args) = parser.parse_args(args)
        # make assoc array options in to a dict
        options = vars(options)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'first pass: {options}:{op_args}')
        # find first pass actions (i.e. whine log level '-w' settings)
        for k, v in options.items():
            fp_action_meta = self.first_pass_by_option.get(k)
            if fp_action_meta is not None:
                options = {k: options[k] for k in (set(options.keys()) & fp_opts)}
                actions.append(Action(fp_action_meta, options, ()))
        # if only one option for second pass actions are given, the user need
        # not give the action mnemonic/name, instead, just add all its options
        # to the top level
        if len(self.second_pass_actions) == 1:
            action_name = self.second_pass_actions[0].name
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'using singeton top level action: {action_name}')
        elif len(op_args) == 0:
            # no positional arguments mean we don't know which action to use
            raise CommandLineError('no action given')
        else:
            # otherwise, use the first positional parameter as the mnemonic and
            # the remainder as positional parameters for that action
            action_name = op_args[0]
            op_args = op_args[1:]
            second_pass = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'need second pass for {action_name}, ' +
                             f'option args: {op_args}')
        action_meta = self.actions_by_name.get(action_name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"action '{action_name}' found: {action_meta}")
        if action_meta is None:
            raise CommandLineError(f'no such action: {action_name}')
        if len(action_meta.positional) != len(op_args):
            raise CommandLineError(
                f"action '{action_meta.name}' expects " +
                f"{len(action_meta.positional)} " +
                f'arguments but got {len(op_args)}')
        if second_pass:
            parser: OptionParser = self._get_second_pass_parser(action_meta)
            (options, op_args) = parser.parse_args(args)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'second pass: {options}::{op_args}')
            assert(op_args[0] == action_meta.name)
            op_args = op_args[1:]
            options = vars(options)
            options = {k: options[k] for k in (set(options.keys()) - fp_opts)}
        pos_args = self._parse_positional(action_meta.positional, op_args)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating action with {options} {pos_args}')
        action_inst = Action(action_meta, options, pos_args)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'adding action: {action_inst}')
        actions.append(action_inst)
        return ActionSet(tuple(actions))
