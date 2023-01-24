"""Domain classes for parsing the command line.

"""
__author__ = 'Paul Landes'

from typing import Tuple, Dict, Any, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
import sys
import traceback
from io import TextIOBase
from pathlib import Path
import optparse
from frozendict import frozendict
from zensols.introspect import TypeMapper
from zensols.persist import persisted, PersistableContainer
from zensols.config import Dictable
from . import ActionCliError

logger = logging.getLogger(__name__)


class ApplicationError(ActionCliError):
    """Thrown for any application error that should result in a user error
    rather than produce a full stack trace.

    """
    pass


@dataclass
class ApplicationFailure(Dictable):
    """Contains information for application invocation failures used by
    programatic methods.

    """
    exception: Exception = field()
    """The exception that was generated."""

    thrower: Any = field(default=None)
    """The insstance of the class that is throwing the exception."""

    traceback: traceback = field(default=None, repr=False)
    """The stack trace."""

    def __post_init__(self):
        self._exec_info = sys.exc_info()
        if self.traceback is None:
            self.traceback = self._exec_info[2]

    def print_stack(self):
        traceback.print_exception(*self._exec_info)

    def __str__(self):
        return str(self.exception)


@dataclass
class _MetavarFormatter(object):
    def __post_init__(self):
        if issubclass(self.dtype, Enum) and self.choices is None:
            self.choices = tuple(sorted(self.dtype.__members__.keys()))
        if self.metavar is None:
            self._set_metvar()

    @property
    def is_choice(self) -> bool:
        """Whether or not this option represents string combinations that map to
        a :class:`enum.Enum` Python class.

        """
        return (self.choices is not None) or issubclass(self.dtype, Enum)

    def _set_metvar(self) -> str:
        if self.is_choice:
            metavar = f"<{'|'.join(self.choices)}>"
        elif self.dtype == Path:
            metavar = 'FILE'
        elif self.dtype == bool:
            metavar = None
        elif self.dtype == str:
            metavar = 'STRING'
        else:
            metavar = self.dtype.__name__.upper()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'metavar recompute using {self.dtype}: ' +
                         f'{metavar}, {self.choices}')
        self.metavar = metavar


@dataclass(eq=True, order=True, unsafe_hash=True)
class OptionMetaData(PersistableContainer, Dictable, _MetavarFormatter):
    """A command line option."""

    DATA_TYPES = frozenset(TypeMapper.DEFAULT_DATA_TYPES.values())
    """Supported data types."""

    long_name: str = field()
    """The long name of the option (i.e. ``--config``)."""

    short_name: str = field(default=None)
    """The short name of the option (i.e. ``-c``)."""

    dest: str = field(default=None, repr=False)
    """The the field/parameter name used to on the target class."""

    dtype: type = field(default=str)
    """The data type of the option (i.e. :class:`str`).

    Other types include: :class:`int`, :class`float`, :class:`bool`,
    :class:`list` (for choice), or :class:`patlib.Path` for files and
    directories.

    """
    choices: Tuple[str, ...] = field(default=None)
    """The constant list of choices when :obj:`dtype` is :class:`list`.  Note
    that this class is a tuple so instances are hashable in :class:`.ActionCli`.

    """
    default: str = field(default=None)
    """The default value of the option."""

    doc: str = field(default=None)
    """The document string used in the command line help."""

    metavar: str = field(default=None, repr=False)
    """Used in the command line help for the type of the option."""

    def __post_init__(self):
        if self.dest is None:
            self.dest = self.long_name
        _MetavarFormatter.__post_init__(self)

    def _str_vals(self) -> Tuple[str, str, str]:
        default = self.default
        choices = None
        tpe = {str: 'string',
               int: 'int',
               float: 'float',
               bool: None,
               Path: None,
               list: 'choice'}.get(self.dtype)
        if tpe is None and self.is_choice:
            tpe = 'choice'
            choices = self.choices
        # use the string value of the default if set from the enum
        if isinstance(default, Enum):
            default = default.name
        elif (default is not None) and (self.dtype != bool):
            default = str(default)
        return tpe, default, choices

    @property
    def default_str(self) -> str:
        """Get the default as a string usable in printing help and as a default
        using the :class:`optparse.OptionParser` class.

        """
        return self._str_vals()[1]

    @property
    def long_option(self) -> str:
        """The long option string with dashes."""
        return f'--{self.long_name}'

    @property
    def short_option(self) -> str:
        """The short option string with dash."""
        return None if self.short_name is None else f'-{self.short_name}'

    def create_option(self) -> optparse.Option:
        """Add the option to an option parser.

        :param parser: the parser to populate

        """
        params = {}
        tpe, default, choices = self._str_vals()
        if choices is not None:
            params['choices'] = choices
        # only set the default if given, as default=None is not the same as a
        # missing default when adding the option
        if default is not None:
            params['default'] = default
        if tpe is not None:
            params['type'] = tpe
        if self.dtype == list:
            params['choices'] = self.choices
        if self.doc is not None:
            params['help'] = self.doc
        for att in 'metavar dest'.split():
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
        return optparse.Option(self.long_option, self.short_option, **params)

    def _from_dictable(self, *args, **kwargs) -> Dict[str, Any]:
        dct = super()._from_dictable(*args, **kwargs)
        dct['dtype'] = self.dtype
        if not self.is_choice:
            del dct['choices']
        else:
            if self.default is not None:
                dct['default'] = self.default.name
        dct = {k: dct[k] for k in
               filter(lambda x: dct[x] is not None, dct.keys())}
        return dct

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        dct = self.asdict()
        del dct['long_name']
        self._write_line(self.long_name, depth, writer)
        self._write_object(dct, depth + 1, writer)


@dataclass
class PositionalMetaData(Dictable, _MetavarFormatter):
    """A command line required argument that has no option switches.

    """
    name: str = field()
    """The name of the positional argument.  Used in the documentation and when
    parsing the type.

    """
    dtype: Type = field(default=str)
    """The type of the positional argument.

    :see: :obj:`.Option.dtype`

    """
    doc: str = field(default=None)
    """The documentation of the positional metadata or ``None`` if missing.

    """
    choices: Tuple[str, ...] = field(default=None)
    """The constant list of choices when :obj:`dtype` is :class:`list`.  Note
    that this class is a tuple so instances are hashable in :class:`.ActionCli`.

    """
    metavar: str = field(default=None, repr=False)
    """Used in the command line help for the type of the option."""

    def __post_init__(self):
        _MetavarFormatter.__post_init__(self)


class OptionFactory(object):
    """Creates commonly used options.

    """
    @classmethod
    def dry_run(cls: type, **kwargs) -> OptionMetaData:
        """A boolean dry run option."""
        return OptionMetaData('dry_run', 'd', dtype=bool,
                              doc="don't do anything; just act like it",
                              **kwargs)

    @classmethod
    def file(cls: type, name: str, short_name: str, **kwargs):
        """A file :class:`~pathlib.Path` option."""
        return OptionMetaData(name, short_name, dtype=Path,
                              doc=f'the path to the {name} file',
                              **kwargs)

    @classmethod
    def directory(cls: type, name: str, short_name: str, **kwargs):
        """A directory :class:`~pathlib.Path` option."""
        return OptionMetaData(name, short_name, dtype=Path,
                              doc=f'the path to the {name} directory',
                              **kwargs)

    @classmethod
    def config_file(cls: type, **kwargs) -> OptionMetaData:
        """A subordinate file based configuration option."""
        return cls.file('config', 'c', **kwargs)


@dataclass
class ActionMetaData(PersistableContainer, Dictable):
    """An action represents a link between a command line mnemonic *action* and
    a method on a class to invoke.

    """
    _DICTABLE_WRITABLE_DESCENDANTS = True

    name: str = field(default=None)
    """The name of the action, which is also the mnemonic used on the command
    line.

    """
    doc: str = field(default=None)
    """A short human readable documentation string used in the usage."""

    options: Tuple[OptionMetaData, ...] = field(default_factory=lambda: ())
    """The command line options for the action."""

    positional: Tuple[PositionalMetaData, ...] = \
        field(default_factory=lambda: ())
    """The positional arguments expected for the action."""

    first_pass: bool = field(default=False)
    """If ``True`` this is a first pass action that is used with no mnemonic.
    Examples include the ``-w``/``--whine`` logging level, which applies to the
    entire application and can be configured in a separate class/process from
    the main single action given as a mnemonic on the command line.

    """
    is_usage_visible: bool = field(default=True)
    """Whether to display the action in the help usage.  Applications such as
    :class:`.ConfigFactoryAccessor`, which is only useful with a programatic
    usage, is an example of where this is used.

    """
    def __post_init__(self):
        if self.first_pass and len(self.positional) > 0:
            raise ActionCliError(
                'A first pass action can not have positional arguments, ' +
                f'but got {self.positional} for action: {self.name}')

    @property
    @persisted('_options_by_dest')
    def options_by_dest(self) -> Dict[str, OptionMetaData]:
        return frozendict({m.dest: m for m in self.options})

    def _from_dictable(self, *args, **kwargs) -> Dict[str, Any]:
        dct = super()._from_dictable(*args, **kwargs)
        if len(dct['positional']) == 0:
            del dct['positional']
        return dct
