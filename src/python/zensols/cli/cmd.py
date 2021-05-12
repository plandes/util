"""Classes to parse command line arguments.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Any, Dict, Iterable
from dataclasses import dataclass, field
from enum import Enum
import logging
import sys
from itertools import chain
from pathlib import Path
from io import TextIOBase
from optparse import OptionParser
from zensols.persist import persisted, PersistableContainer, Deallocatable
from zensols.config import Dictable
from . import (
    ActionCliError, OptionMetaData, PositionalMetaData, ActionMetaData,
    UsageActionOptionParser,
)

logger = logging.getLogger(__name__)


class CommandLineError(ActionCliError):
    """Raised when command line parameters can not be parsed.

    """
    pass


class CommandLineConfigError(Exception):
    """Programmer error for command line parser configuration errors.

    """
    pass


@dataclass
class CommandAction(Dictable):
    """The output of the :class:`.CommandLineParser` for each parsed action.

    """
    WRITABLE__DESCENDANTS = True

    meta_data: ActionMetaData = field()
    """The action parsed from the command line."""

    options: Dict[str, Any] = field()
    """The options given as switches."""

    positional: Tuple[str] = field()
    """The positional arguments parsed."""

    @property
    def name(self) -> str:
        """The name of the action."""
        return self.meta_data.name

    def __str__(self) -> str:
        return f'{self.meta_data.name}: {self.options}/{self.positional}'


@dataclass
class CommandActionSet(Deallocatable, Dictable):
    """The actions that are parsed by :class:`.CommandLineParser` as the output of
    the parse phase.  This is indexable by command action name and iterable
    across all actions.  Properties :obj:`first_pass_actions` and
    :obj:`second_pass_action` give access to the split from the respective
    types of actions.

    """
    WRITABLE__DESCENDANTS = True

    actions: Tuple[CommandAction] = field()
    """The actions parsed.  The first N actions are first pass where as the last is
    the second pass action.

    """
    @property
    def first_pass_actions(self) -> Iterable[CommandAction]:
        """All first pass actions."""
        return self.actions[0:-1]

    @property
    def second_pass_action(self) -> CommandAction:
        """The single second pass action."""
        return self.actions[-1]

    @property
    def by_name(self) -> Dict[str, CommandAction]:
        """Command actions by name keys."""
        return {a.name: a for a in self.actions}

    def deallocate(self):
        super().deallocate()
        self._try_deallocate(self.actions)

    def __getitem__(self, name: str) -> CommandAction:
        return self.by_name[name]

    def __iter__(self) -> Iterable[CommandAction]:
        return iter(self.actions)

    def __len__(self) -> int:
        return len(self.actions)


@dataclass
class CommandLineConfig(PersistableContainer, Dictable):
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
            for k, v in action.options_by_dest.items():
                if k in actions:
                    raise CommandLineConfigError(
                        f"First pass duplicate option in '{action.name}': {k}")
                actions[k] = action
        return actions

    def deallocate(self):
        super().deallocate()
        self._try_deallocate(self.actions)


@dataclass
class CommandLineParser(Deallocatable, Dictable):
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
    config: CommandLineConfig = field()
    """Configures the command line parser with the action meta data."""

    version: str = field(default='v0')
    """The version of the application, which is used in the help and the
    ``--version`` switch.

    """

    default_action: str = field(default=None)
    """The default mnemonic use when the user does not supply one."""

    application_doc: str = field(default=None)
    """The program documentation to use when it can not be deduced from the action.

    """

    def __post_init__(self):
        if len(self.config.actions) == 0:
            raise CommandLineConfigError(
                'Must create parser with at least one action')

    def _create_parser(self, actions: Tuple[ActionMetaData]) -> OptionParser:
        return UsageActionOptionParser(
            actions,
            self.application_doc,
            self.default_action,
            version=('%prog ' + str(self.version)))

    def _configure_parser(self, parser: OptionParser,
                          options: Iterable[OptionMetaData]):
        opt_names = set()
        for opt in options:
            if opt.long_name in opt_names:
                raise CommandLineConfigError(
                    f'Duplicate option: {opt.long_name}')
            opt_names.add(opt.long_name)
            op_opt = opt.create_option()
            parser.add_option(op_opt)

    def _get_first_pass_parser(self, add_all_opts: bool) -> \
            UsageActionOptionParser:
        opts = list(self.config.first_pass_options)
        sp_actions = self.config.second_pass_actions
        if len(sp_actions) == 1:
            sp_actions = (sp_actions[0],)
            opts.extend(sp_actions[0].options)
        elif add_all_opts:
            opts.extend(chain.from_iterable(
                map(lambda a: a.options, sp_actions)))
        parser = self._create_parser(sp_actions)
        self._configure_parser(parser, set(opts))
        return parser

    def _get_second_pass_parser(self, action_meta: ActionMetaData) -> \
            UsageActionOptionParser:
        opts = list(self.config.first_pass_options)
        opts.extend(action_meta.options)
        parser = self._create_parser(self.config.second_pass_actions)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"creating parser for action: '{action_meta.name}' " +
                         f'opts: {action_meta.options}')
        self._configure_parser(parser, opts)
        return parser

    def write_help(self, writer: TextIOBase = sys.stdout,
                   include_actions: bool = True):
        """Write the usage information and help text.

        :param include_actions: if ``True`` write each actions' usage as well

        """
        parser = self._get_first_pass_parser(False)
        parser.print_help(writer, include_actions)

    def error(self, msg: str):
        """Print a usage with the error message and exit the program as fail.

        """
        parser = self._get_first_pass_parser(False)
        parser.error(msg)

    def _parse_type(self, s: str, t: type, name: str) -> Any:
        tpe = None
        if issubclass(t, Enum):
            tpe = t.__members__.get(s)
            choices = ', '.join(map(lambda e: f"'{e.name}'", t))
            if tpe is None:
                raise CommandLineError(
                    f"No choice '{s}' for '{name}' (choose from {choices})")
        else:
            if not isinstance(s, (str, int, float, bool, Path)):
                raise CommandLineConfigError(f'Unknown parse type: {s}: {t}')
            try:
                tpe = t(s)
            except ValueError as e:
                raise CommandLineError(f'Expecting type {t.__name__}: {e}')
        return tpe

    def _parse_options(self, action_meta: ActionMetaData,
                       op_args: Dict[str, Any]):
        opts: Dict[str, OptionMetaData] = action_meta.options_by_dest
        parsed = {}
        for k, v in op_args.items():
            opt: OptionMetaData = opts.get(k)
            if v is not None and opt is not None:
                v = self._parse_type(v, opt.dtype, opt.long_option)
            parsed[k] = v
        return parsed

    def _parse_positional(self, metas: List[PositionalMetaData],
                          vals: List[str]) -> Tuple[Any]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing positional args: {metas} <--> {vals}')
        return tuple(
            map(lambda x: self._parse_type(x[0], x[1].dtype, x[1].name),
                zip(vals, metas)))

    def _parse_first_pass(self, args: List[str],
                          actions: List[CommandAction]) -> \
            Tuple[bool, str, Dict[str, Any], Dict[str, Any], Tuple[str]]:
        second_pass = False
        fp_opts = set(map(lambda o: o.dest, self.config.first_pass_options))
        # first fish out the action name (if given) as a positional parameter
        parser: OptionParser = self._get_first_pass_parser(True)
        (options, op_args) = parser.parse_args(args)
        # make assoc array options in to a dict
        options = vars(options)
        if options['help'] is True:
            self.write_help()
            sys.exit(0)
        else:
            del options['help']
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'first pass: {options}:{op_args}')
        # find first pass actions (i.e. whine log level '-w' settings)
        added_first_pass = set()
        fp_ops: Dict[str, ActionMetaData] = self.config.first_pass_by_option
        for k, v in options.items():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'looking for first pass option: {k} ' +
                             f'in {tuple(fp_ops.keys())}')
            fp_action_meta = fp_ops.get(k)
            if (fp_action_meta is not None) and \
               (fp_action_meta.name not in added_first_pass):
                aos = {k: options[k] for k in (set(options.keys()) & fp_opts)}
                aos = self._parse_options(fp_action_meta, aos)
                action = CommandAction(fp_action_meta, aos, ())
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'adding first pass action: {action}')
                actions.append(action)
                added_first_pass.add(fp_action_meta.name)
        # if only one option for second pass actions are given, the user need
        # not give the action mnemonic/name, instead, just add all its options
        # to the top level
        if len(self.config.second_pass_actions) == 1:
            action_name = self.config.second_pass_actions[0].name
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'using singleton fp action: {action_name} ' +
                             f'with options {options}')
        elif len(op_args) == 0:
            if self.default_action is None:
                # no positional arguments mean we don't know which action to
                # use
                raise CommandLineError('No action given')
            else:
                action_name = self.default_action
                op_args = []
                args = [action_name] + args
                second_pass = True
        else:
            # otherwise, use the first positional parameter as the mnemonic and
            # the remainder as positional parameters for that action
            action_name = op_args[0]
            op_args = op_args[1:]
            second_pass = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'need second pass for {action_name}, ' +
                             f'option args: {op_args}')
        return second_pass, action_name, fp_opts, options, op_args, args

    def _parse_second_pass(self, action_name: str, second_pass: bool,
                           args: List[str], options: Dict[str, Any],
                           op_args: Tuple[str]):
        # now that we have parsed the action name, get the meta data
        action_meta: ActionMetaData = \
            self.config.actions_by_name.get(action_name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"action '{action_name}' found: {action_meta}")
        if action_meta is None:
            raise CommandLineError(f'No such action: {action_name}')
        pos_arg_diff = len(op_args) - len(action_meta.positional)
        single_sp = None
        if len(self.config.second_pass_actions) == 1:
            single_sp = self.config.second_pass_actions[0].name
        unnecessary_mnemonic = pos_arg_diff == 1 and single_sp == op_args[0]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'positional arg difference: {pos_arg_diff}, ' +
                         f'single second pass mnemonic: {single_sp}, ' +
                         f'unnecessary_mnemonic: {unnecessary_mnemonic}')
        if unnecessary_mnemonic:
            raise CommandLineError(
                f"Action '{action_meta.name}' expects " +
                f"{len(action_meta.positional)} argument(s), but " +
                f"'{single_sp}' is counted as a positional argument " +
                'and should be omitted')
        if pos_arg_diff != 0:
            raise CommandLineError(
                f"Action '{action_meta.name}' expects " +
                f"{len(action_meta.positional)} " +
                f"argument(s) but got {len(op_args)}: {', '.join(op_args)}")
        # if there is more than one second pass action, we must re-parse using
        # the specific options and positional argument for that action
        if second_pass:
            parser: OptionParser = self._get_second_pass_parser(action_meta)
            (options, op_args) = parser.parse_args(args)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'second pass opts: {options}:{op_args}')
            # sanity check to match parsed mnemonic and action name
            assert(op_args[0] == action_meta.name)
            # remove the action name
            op_args = op_args[1:]
            options = vars(options)
            del options['help']
        options = self._parse_options(action_meta, options)
        return action_meta, options, op_args

    def _validate_setup(self):
        """Make sure we don't have a default action with positional args."""
        if self.default_action is not None:
            action_meta: ActionMetaData
            for action_meta in self.config.second_pass_actions:
                if len(action_meta.positional) > 0:
                    raise CommandLineConfigError(
                        'No positional arguments allowed when default ' +
                        f"action '{self.default_action}' " +
                        f'given for method {action_meta.name}')

    def deallocate(self):
        super().deallocate()
        self._try_deallocate(self.config)

    def parse(self, args: List[str]) -> CommandActionSet:
        """Parse command line arguments.

        :param args: the arguments given on the command line; which is usually
                     ``sys.args[1:]``

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing: {args}')
        # action instances
        actions: List[CommandAction] = []
        # some top level sanity checks
        self._validate_setup()
        # first pass parse
        second_pass, action_name, fp_opts, options, op_args, args = \
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
