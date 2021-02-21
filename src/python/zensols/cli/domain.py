"""Domain classes for parsing the command line.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List
from dataclasses import dataclass, field
import logging
from pathlib import Path
from optparse import OptionParser
import optparse
from zensols.config import Dictable

logger = logging.getLogger(__name__)


@dataclass
class Option(Dictable):
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
                self.metavar = str(self.dtype).upper()

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
        for att in 'metavar dest'.split():
            v = getattr(self, att)
            if v is not None:
                params[att] = v
        if self.dtype == bool:
            if self.default is True:
                params['action'] = 'store_false'
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'params: {params}')
        return optparse.Option(long_name, short_name, **params)


class OptionFactory(object):
    """Creates commonly used options.

    """
    @classmethod
    def dry_run(cls: type) -> Option:
        return Option('dry_run', 'd', dtype=bool,
                      doc="don't do anything; just act like it")

    @classmethod
    def file(cls: type, name: str, short_name: str):
        return Option(name, short_name, dtype=Path,
                      doc=f'the path to the {name} file')

    @classmethod
    def config_file(cls: type) -> Option:
        return cls.file('config', 'c')


@dataclass
class Action(Dictable):
    """An action represents a link between a command line mnemonic *action* and a
    method on a class to invoke.

    """
    name: str = field(default=None)
    """The name of the action, which is also the mnemonic used on the command line.
    If ``None``, then the action is the *top level* action when no mnemonic is
    given.

    """

    doc: str = field(default=None)
    """A short human readable documentation string used in the usage."""

    options: Tuple[Option] = field(default_factory=lambda: ())
    """The command line options for the action."""
