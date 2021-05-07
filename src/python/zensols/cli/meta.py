"""Domain classes for parsing the command line.

"""
__author__ = 'Paul Landes'

from typing import Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import sys
from io import TextIOBase
from pathlib import Path
import optparse
from zensols.introspect import TypeMapper
from zensols.persist import persisted, PersistableContainer
from zensols.config import Dictable
from . import ActionCliError

logger = logging.getLogger(__name__)


@dataclass(eq=True, order=True, unsafe_hash=True)
class OptionMetaData(PersistableContainer, Dictable):
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

    Other types include: :class:`int`, :class`float`, :clas:`bool`,
    :class:`list` (for choice), or :class:`patlib.Path` for files and
    directories.

    """

    choices: Tuple[str] = field(default=None)
    """The constant list of choices when :obj:`dtype` is :class:`list`.  Note that
    this class is a tuple so instances are hashable in :class:`.ActionCli`.

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
        if issubclass(self.dtype, Enum) and self.choices is None:
            self.choices = tuple(sorted(self.dtype.__members__.keys()))
        if self.metavar is None:
            self._set_metavar()

    @property
    def is_choice(self) -> bool:
        """Whether or not this option represents string combinations that map to a
        :class:`enum.Enum` Python class.

        """
        return (self.choices is not None) or issubclass(self.dtype, Enum)

    def _set_metavar(self, clobber: bool = True):
        if self.is_choice:
            self.metavar = f"<{'|'.join(self.choices)}>"
        elif self.dtype == Path:
            self.metavar = 'FILE'
        elif self.dtype == bool:
            self.metavar = None
        elif self.dtype == str:
            self.metavar = 'STRING'
        else:
            self.metavar = self.dtype.__name__.upper()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'metavar recompute using {self.dtype}: ' +
                         f'{self.metavar}, {self.choices}')

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
        """Get the default as a string usable in printing help and as a default using
        the :class:`optparse.OptionParser` class.

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
        dct['dtype'] = self.dtype.__name__
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
    """An action represents a link between a command line mnemonic *action* and a
    method on a class to invoke.

    """
    WRITABLE__DESCENDANTS = True

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
            raise ActionCliError(
                'A first pass action can not have positional arguments, ' +
                f'but got {self.positional} for action: {self.name}')

    @property
    @persisted('_options_by_dest')
    def options_by_dest(self) -> Dict[str, OptionMetaData]:
        return {m.dest: m for m in self.options}

    def _from_dictable(self, *args, **kwargs) -> Dict[str, Any]:
        dct = super()._from_dictable(*args, **kwargs)
        if len(dct['positional']) == 0:
            del dct['positional']
        return dct
