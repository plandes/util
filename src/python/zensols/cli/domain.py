"""Domain classes for parsing the command line.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Dict, Iterable, Any
from dataclasses import dataclass, field
import logging
from pathlib import Path
import optparse
from zensols.persist import persisted
from zensols.config import Dictable
from . import ActionCliError

logger = logging.getLogger(__name__)


class CommandLineError(ActionCliError):
    """Raised when command line parameters can not be parsed.

    """
    pass


@dataclass(eq=True, order=True, unsafe_hash=True)
class OptionMetaData(Dictable):
    """A command line option."""

    long_name: str = field()
    """The long name of the option (i.e. ``--config``)."""

    short_name: str = field(default=None)
    """The short name of the option (i.e. ``-c``)."""

    dest: str = field(default=None)
    """The the field/parameter name used to on the target class."""

    dtype: type = field(default=str)
    """The data type of the option (i.e. :class:`str`).

    Other types include: :class:`int`, :class`float`, :clas:`bool`,
    :class:`list` (for choice), or :class:`patlib.Path` for files and
    directories.

    """

    choices: List[str] = field(default=None)
    """The constant list of choices when :obj:`dtype` is :class:`list`."""

    default: str = field(default=None)
    """The default value of the option."""

    doc: str = field(default=None)
    """The document string used in the command line help."""

    metavar: str = field(default=None)
    """Used in the command line help for the type of the option."""

    required: bool = field(default=False)
    """Whether or not the target class expects the option to be set."""

    def __post_init__(self):
        if self.dest is None:
            self.dest = self.long_name
        if self.metavar is None:
            if self.dtype == list:
                self.metavar = '|'.join(self.choices)
            elif self.dtype == Path:
                self.metavar = 'FILE'
            elif self.dtype == bool:
                self.metavar = None
            else:
                self.metavar = self.dtype.__name__

    def create_option(self) -> optparse.Option:
        """Add the option to an option parser.

        :param parser: the parser to populate

        """
        tpe = {str: 'string',
               int: 'int',
               float: 'float',
               bool: None,
               Path: None,
               list: 'choice'}[self.dtype]
        params = {}
        long_name = f'--{self.long_name}'
        short_name = None if self.short_name is None else f'-{self.short_name}'
        if tpe is not None:
            params['type'] = tpe
        if self.dtype == list:
            params['choices'] = self.choices
        if self.doc is not None:
            params['help'] = self.doc
        for att in 'metavar dest default'.split():
            v = getattr(self, att)
            if v is not None:
                params[att] = v
        if self.dtype == bool:
            if self.default is True:
                params['action'] = 'store_false'
            else:
                params['action'] = 'store_true'
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'params: {params}')
        return optparse.Option(long_name, short_name, **params)


@dataclass
class PositionalMetaData(Dictable):
    """A command line required argument that has no option switches.

    """
    name: str = field()
    """The name of the positional argument.  Used in the documentation and when
    parsing the type.

    """

    dtype: type = field(default=str)
    """The type of the positional argument.

    :see: :obj:`.Option.dtype`

    """


class OptionFactory(object):
    """Creates commonly used options.

    """
    @classmethod
    def dry_run(cls: type, **kwargs) -> OptionMetaData:
        return OptionMetaData('dry_run', 'd', dtype=bool,
                              doc="don't do anything; just act like it",
                              **kwargs)

    @classmethod
    def file(cls: type, name: str, short_name: str, **kwargs):
        return OptionMetaData(name, short_name, dtype=Path,
                              doc=f'the path to the {name} file',
                              **kwargs)

    @classmethod
    def config_file(cls: type, **kwargs) -> OptionMetaData:
        return cls.file('config', 'c', **kwargs)

    @classmethod
    def whine_level(cls: type, **kwargs) -> OptionMetaData:
        return OptionMetaData('whine', 'w', dtype=int,
                              doc='the level to set for the program logging')


@dataclass
class ActionMetaData(Dictable):
    """An action represents a link between a command line mnemonic *action* and a
    method on a class to invoke.

    """
    name: str = field(default=None)
    """The name of the action, which is also the mnemonic used on the command line.

    """

    doc: str = field(default=None)
    """A short human readable documentation string used in the usage."""

    options: Tuple[OptionMetaData] = field(default_factory=lambda: ())
    """The command line options for the action."""

    positional: Tuple[PositionalMetaData] = field(default_factory=lambda: ())
    """The positional arguments expected for the action."""

    first_pass: bool = field(default=False)
    """If ``True`` this is a first pass action that is used with no mnemonic.
    Examples include the ``-w``/``--whine`` logging level, which applies to the
    entire application and can be configured in a separate class/process from
    the main single action given as a mnemonic on the command line.

    """

    def __post_init__(self):
        if self.first_pass and len(self.positional) > 0:
            raise ValueError(
                'a first pass action can not have positional arguments')

    @property
    @persisted('_options_by_name')
    def options_by_name(self) -> Dict[str, OptionMetaData]:
        return {m.long_name: m for m in self.options}


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
        """The name of the action."""
        return self.meta_data.name


@dataclass
class ActionSet(Dictable):
    """The actions that are parsed by :class:`.CommandLineParser`.

    """
    actions: Tuple[Action] = field()
    """The actions parsed.  The first N actions are first pass where as the last is
    the second pass action.

    """

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
