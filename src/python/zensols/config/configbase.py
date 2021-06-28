from __future__ import annotations
"""Abstract base class for a configuration read from a file.

"""
__author__ = 'Paul Landes'

from typing import Dict, Set, Iterable, List, Any, Union
from abc import ABCMeta, abstractmethod
import logging
from pathlib import Path
import sys
from io import TextIOBase
import inspect
from . import ConfigurationError, Serializer, Writable, Settings

logger = logging.getLogger(__name__)


class ConfigurableError(ConfigurationError):
    """Base class raised for any configuration based errors."""
    pass


class ConfigurableFileNotFoundError(ConfigurableError):
    """Raised when a configuration file is not found for those file based instances
    of :class:`.Configurable`.

    """
    def __init__(self, path: Path):
        super().__init__(f'No such file: {path}')
        self.path = path


class Configurable(Writable, metaclass=ABCMeta):
    """An abstract base class that represents an application specific
    configuration.

    Note that many of the getters are implemented in ``configparser``.
    However, they are reimplemented here for consistency among parser.

    """
    def __init__(self, default_section: str = None):
        """Initialize.

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`

        """
        if default_section is None:
            self.default_section = 'default'
        else:
            self.default_section = default_section
        self.serializer = Serializer()

    @abstractmethod
    def get_options(self, section: str = None) -> Dict[str, str]:
        """Get all options for a section.  If ``opt_keys`` is given return only
        options with those keys.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        """
        pass

    @abstractmethod
    def has_option(self, name: str, section: str = None) -> bool:
        pass

    def get_option(self, name: str, section: str = None) -> str:
        """Return an option from ``section`` with ``name``.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        """
        val = None
        opts = self.get_options(section or self.default_section)
        if opts is not None:
            val = opts.get(name)
        if val is None:
            raise ConfigurableError(
                f"No option '{name}' found in section: {section}")
        return val

    def reload(self):
        """Reload the configuration from the backing store.

        """
        pass

    def get_option_list(self, name: str, section: str = None) -> List[str]:
        """Just like :meth:`get_option` but parse as a list using ``split``.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        """
        val = self.get_option(name, section)
        return self.serializer.parse_list(val)

    def get_option_boolean(self, name: str, section: str = None) -> bool:
        """Just like :meth:`get_option` but parse as a boolean (any case `true`).

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        """
        val = self.get_option(name, section)
        val = val.lower() if val else 'false'
        return val == 'true'

    def get_option_int(self, name: str, section: str = None):
        """Just like :meth:`get_option` but parse as an integer.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        """
        val = self.get_option(name, section)
        if val:
            return int(val)

    def get_option_float(self, name: str, section: str = None):
        """Just like :meth:`get_option` but parse as a float.

        """
        val = self.get_option(name, section)
        if val:
            return float(val)

    def get_option_path(self, name: str, section: str = None):
        """Just like :meth:`get_option` but return a ``pathlib.Path`` object of the
        string.

        """
        val = self.get_option(name, section)
        path = None
        if val is not None:
            path = Path(val)
        return path

    def get_option_object(self, name: str, section: str = None):
        """Just like :meth:`get_option` but parse as an object per object syntax
        rules.

        :see: :meth:`parse_object`

        """
        val = self.get_option(name, section)
        if val:
            return self.serializer.parse_object(val)

    @property
    def options(self) -> Dict[str, str]:
        """Return all options from the default section.

        """
        return self.get_options()

    def populate(self, obj: Any = None, section: str = None,
                 parse_types: bool = True) -> Union[dict, Settings]:
        """Set attributes in ``obj`` with ``setattr`` from the all values in
        ``section``.

        """
        section = self.default_section if section is None else section
        sec = self.get_options(section)
        if sec is None:
            # needed for the YamlConfig class
            raise ConfigurableError(
                f"No section from which to populate: '{section}'")
        return self.serializer.populate_state(sec, obj, parse_types)

    @property
    def sections(self) -> Set[str]:
        """All sections of the configuration file.

        """
        return ()

    def set_option(self, name: str, value: str, section: str = None):
        """Set an option on this configurable.

        :param name: the name of the option

        :param value: the value to set

        :param section: the section (if applies) to add the option

        :raises NotImplementedError: if this class does not support this
                                     operation

        """
        raise NotImplementedError()

    def copy_sections(self, to_populate: Configurable,
                      sections: Iterable[str] = None,
                      robust: bool = False) -> Exception:
        """Copy all sections from this configuruable to ``to_populate``.

        :param to_populate: the target configuration object

        :param sections: the sections to populate or ``None`` to copy allow

        :param robust: if ``True``, when any exception occurs (namely
                       interplation exceptions), don't copy and remove the
                       section in the target configuraiton

        :return: the last exception that occured while trying to copy the
                 properties

        """
        last_ex = None
        if sections is None:
            sections = self.sections
        for sec in sections:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'copying section {sec}')
            try:
                for k, v in self.get_options(sec).items():
                    to_populate.set_option(k, v, sec)
            # robust is needed by lib.ConfigurationImporter_load(); but deal
            # only with interplation errors
            except ConfigurableError as e:
                raise e
            except Exception as e:
                if not robust:
                    raise e
                else:
                    to_populate.remove_section(sec)
                    last_ex = e
        return last_ex

    def remove_section(self, section: str):
        """Remove a seciton with the given name."""
        raise NotImplementedError()

    def merge(self, to_populate: Configurable):
        """Copy all data from this configuruable to ``to_populate``, and clobber any
        overlapping properties in the process.

        :param to_populate: the target configuration object

        """
        to_populate.copy_sections(self, to_populate.sections)

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Print a human readable list of sections and options.

        """
        for sec in sorted(self.sections):
            self._write_line(sec, depth, writer)
            for k, v in self.get_options(sec).items():
                self._write_line(f'{k}: {v}', depth + 1, writer)

    def _get_calling_module(self, depth: int = 0):
        """Get the last module in the call stack that is not this module or ``None`` if
        the call originated from this module.

        """
        for frame in inspect.stack():
            mod = inspect.getmodule(frame[depth])
            logger.debug(f'calling module: {mod}')
            if mod is not None:
                mod_name = mod.__name__
                if mod_name != __name__:
                    return mod

    def resource_filename(self, resource_name: str, module_name: str = None):
        """Return a resource based on a file name.  This uses the ``pkg_resources``
        package first to find the resources.  If it doesn't find it, it returns
        a path on the file system.

        :param: resource_name the file name of the resource to obtain (or name
                if obtained from an installed module)

        :param module_name: the name of the module to obtain the data, which
                            defaults to ``__name__``

        :return: a path on the file system or resource of the installed module

        """
        if module_name is None:
            mod = self._get_calling_module()
            logger.debug(f'calling module: {mod}')
            if mod is not None:
                module_name = mod.__name__
        return self.serializer.resource_filename(resource_name, module_name)
