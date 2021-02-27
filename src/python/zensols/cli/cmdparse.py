"""Classes to parse command line arguments.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Any, Dict, Iterable, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
import sys
from itertools import chain
from pathlib import Path
from io import TextIOBase
from optparse import OptionParser
from zensols.persist import persisted
from zensols.config import Dictable
from . import (
    CommandLineError, UsageWriter,
    OptionMetaData, PositionalMetaData, ActionMetaData,
    CommandAction, CommandActionSet,
)

logger = logging.getLogger(__name__)


class ActionOptionParser(OptionParser):
    """Implements a human readable implementation of print_help for action based
    command line handlers.

    **Implementation note**: we have to extend :class:`~optparser.OptionParser`
    since the ``-h`` option invokes the print help behavior and then exists.

    """
    def __init__(self, actions: Tuple[ActionMetaData], doc: str = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usage_writer = UsageWriter(self, actions, doc)

    def print_help(self, file=sys.stdout):
        super().print_help(file)
        self.usage_writer.write(writer=file)


@dataclass
class CommandLineConfig(Dictable):
    """Given to configure the :class:`.CommandLineParser`.

    """

    actions: Tuple[ActionMetaData] = field()
    """The action meta data used to parse and print help."""

    @property
    @persisted('_first_pass_actions')
    def first_pass_actions(self) -> Tuple[ActionMetaData]:
        return tuple(filter(lambda a: a.first_pass, self.actions))

    @property
    @persisted('_second_pass_actions')
    def second_pass_actions(self) -> Tuple[ActionMetaData]:
        return tuple(filter(lambda a: not a.first_pass, self.actions))

    @property
    @persisted('_actions_by_name')
    def actions_by_name(self) -> Dict[str, ActionMetaData]:
        return {a.name: a for a in self.actions}

    @property
    @persisted('_first_pass_options')
    def first_pass_options(self) -> Tuple[OptionMetaData]:
        return tuple(chain.from_iterable(
            map(lambda a: a.options, self.first_pass_actions)))

    @property
    @persisted('_first_pass_by_option')
    def first_pass_by_option(self) -> Dict[str, ActionMetaData]:
        actions = {}
        for action in self.first_pass_actions:
            for k, v in action.options_by_name.items():
                if k in actions:
                    raise ValueError(
                        f"first pass duplicate option in '{action.name}': {k}")
                actions[k] = action
        return actions


@dataclass
class CommandLineParser(Dictable):
    """Parse the command line.  The parser iterates twice over the command line:

        1. The first pass parses only *first pass* actions
           (:obj:`.ActionMetaData.first_pass`).  This step also is used to
           discover the mnemonic/name of the single second pass action.

        2. The second pass parse parses only a single action that is given on
           the command line.


    The name is given as a mnemonic of the action, unless there is only one
    *second pass action* given, in which case all options and usage are given
    at the top level and a mnemonic is not needed nor parsed.

    :see :obj:`.ActionMetaData.first_pass`

    """
    config: CommandLineConfig

    version: str = field(default='v0')
    """The version of the application, which is used in the help and the
    ``--version`` switch.

    """

    def __post_init__(self):
        if len(self.config.actions) == 0:
            raise ValueError('must create parser with at least one action')

    def _create_program_doc(self) -> Optional[str]:
        doc = None
        if len(self.config.second_pass_actions) == 1:
            doc = self.config.second_pass_actions[0].doc
            doc = doc[0].upper() + doc[1:] + '.'
        return doc

    def _create_parser(self, actions: Tuple[ActionMetaData]) -> OptionParser:
        doc = self._create_program_doc()
        return ActionOptionParser(
            actions, doc, version=('%prog ' + str(self.version)))

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
        opts = list(self.config.first_pass_options)
        sp_actions = self.config.second_pass_actions
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
        opts = list(self.config.first_pass_options)
        opts.extend(action_meta.options)
        parser = self._create_parser(self.config.second_pass_actions)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"creating parser for action: '{action_meta.name}' " +
                         f'opts: {action_meta.options}')
        self._configure_parser(parser, opts)
        return parser

    def write_help(self, writer: TextIOBase = sys.stdout):
        parser = self._get_first_pass_parser(False)
        parser.print_help(file=writer)

    def _parse_positional(self, metas: List[PositionalMetaData],
                          vals: List[str]) -> Tuple[Any]:
        def parse(s: str, t: type) -> Any:
            if issubclass(t, Enum):
                return t.__members__[s]
            else:
                if not isinstance(s, (str, int, bool, Path)):
                    raise ValueError(f'unknown parse type: {s}: {t}')
                return t(s)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing positional args: {metas} <--> {vals}')
        return tuple(map(lambda x: parse(x[0], x[1].dtype), zip(vals, metas)))

    def _parse_first_pass(self, args: List[str],
                          actions: List[CommandAction]) -> \
            Tuple[bool, str, Dict[str, Any], Dict[str, Any], Tuple[str]]:
        second_pass = False
        fp_opts = set(map(lambda o: o.long_name,
                          self.config.first_pass_options))
        # first fish out the action name (if given) as a positional parameter
        parser: OptionParser = self._get_first_pass_parser(True)
        (options, op_args) = parser.parse_args(args)
        # make assoc array options in to a dict
        options = vars(options)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'first pass: {options}:{op_args}')
        # find first pass actions (i.e. whine log level '-w' settings)
        for k, v in options.items():
            fp_action_meta = self.config.first_pass_by_option.get(k)
            if fp_action_meta is not None:
                aos = {k: options[k] for k in (set(options.keys()) & fp_opts)}
                action = CommandAction(fp_action_meta, aos, ())
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'adding first pass action: {action}')
                actions.append(action)
        # if only one option for second pass actions are given, the user need
        # not give the action mnemonic/name, instead, just add all its options
        # to the top level
        if len(self.config.second_pass_actions) == 1:
            action_name = self.config.second_pass_actions[0].name
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'using singleton fp action: {action_name} ' + 
                             f'with options {options}')
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
        return second_pass, action_name, fp_opts, options, op_args

    def _parse_second_pass(self, action_name: str, second_pass: bool,
                           args: List[str], options: Dict[str, Any],
                           op_args: Tuple[str]):
        # now that we have parsed the action name, get the meta data
        action_meta = self.config.actions_by_name.get(action_name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"action '{action_name}' found: {action_meta}")
        if action_meta is None:
            raise CommandLineError(f'no such action: {action_name}')
        if len(action_meta.positional) != len(op_args):
            raise CommandLineError(
                f"action '{action_meta.name}' expects " +
                f"{len(action_meta.positional)} " +
                f'arguments but got {len(op_args)}')
        # if there is more than one second pass action, we must re-parse using
        # the specific options and positional argument for that action
        if second_pass:
            parser: OptionParser = self._get_second_pass_parser(action_meta)
            (options, op_args) = parser.parse_args(args)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'second pass: {options}:{op_args}')
            # sanity check to match parsed mnemonic and action name
            assert(op_args[0] == action_meta.name)
            # remove the action name
            op_args = op_args[1:]
            options = vars(options)
        return action_meta, options, op_args

    def parse(self, args: List[str]) -> CommandActionSet:
        """Parse command line arguments.

        :param args: the arguments given on the command line; which is usually
                     ``sys.args[1:]``

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing: {args}')
        # action instances
        actions: List[CommandAction] = []
        # first pass parse
        second_pass, action_name, fp_opts, options, op_args = \
            self._parse_first_pass(args, actions)
        # second pass parse
        action_meta, options, op_args = self._parse_second_pass(
            action_name, second_pass, args, options, op_args)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'removing first pass options: {fp_opts} ' +
                         f'from {options}')
        # the second pass action should _not_ get the first pass options
        options = {k: options[k] for k in (set(options.keys()) - fp_opts)}
        # parse positional arguments much like the OptionParser did options
        pos_args = self._parse_positional(action_meta.positional, op_args)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating action with {options} {pos_args}')
        # create and add the second pass action
        action_inst = CommandAction(action_meta, options, pos_args)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'adding action: {action_inst}')
        actions.append(action_inst)
        return CommandActionSet(tuple(actions))
