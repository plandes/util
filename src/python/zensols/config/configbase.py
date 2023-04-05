"""Abstract base class for a configuration read from a file.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Dict, Set, Iterable, List, Any, Union, Optional
from abc import ABCMeta, abstractmethod
import sys
import logging
from collections import OrderedDict
import inspect
from pathlib import Path
from io import TextIOBase
import json
from . import ConfigurationError, Serializer, Writable, Settings

logger = logging.getLogger(__name__)


class ConfigurableError(ConfigurationError):
    """Base class raised for any configuration based errors."""
    pass


class ConfigurableFileNotFoundError(ConfigurableError):
    """Raised when a configuration file is not found for those file based instances
    of :class:`.Configurable`.

    """
    def __init__(self, path: Path, source: Union[Path, Any] = None):
        msg = f"No such file: '{path}'"
        if isinstance(source, Path):
            msg += f' loading from {source}'
        super().__init__(msg)
        self.path = path
        self.source = source


class Configurable(Writable, metaclass=ABCMeta):
    """An abstract base class that represents an application specific
    configuration.

    Note that many of the getters are implemented in ``configparser``.
    However, they are reimplemented here for consistency among parser.

    """
    def __init__(self, default_section: str = None):
        """Initialize.

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`;
                                which defaults to ``defualt``

        """
        if default_section is None:
            self.default_section = 'default'
        else:
            self.default_section = default_section
        self.serializer = self._create_serializer()

    def _create_serializer(self) -> Serializer:
        return Serializer()

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

        :see: :meth:`.Serializer.parse_object`

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

    def __getitem__(self, section: str = None) -> Settings:
        return self.populate(section=section)

    @property
    def sections(self) -> Set[str]:
        """All sections of the configuration file.

        """
        return frozenset()

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
                opts: Dict[str, Any] = self.get_options(sec)
                if opts is None:
                    raise ConfigurableError(f"No such section: '{sec}'")
                for k, v in opts.items():
                    to_populate.set_option(k, v, sec)
            # robust is needed by lib.ConfigurationImporter._load(); but deal
            # only with interpolation errors
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
            opts: Dict[str, str] = self.get_options(sec)
            if opts is None:
                raise ConfigurationError(f'No such section: {sec}')
            if not isinstance(opts, dict):
                raise ConfigurationError(
                    f"Expecting dict but got {type(opts)} in section '{sec}'")
            for k in sorted(opts.keys()):
                v = opts[k]
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

    def _get_section_short_str(self):
        try:
            return next(iter(self.sections))
        except StopIteration:
            return ''

    def asdict(self, sort: bool = True) -> Dict[str, Dict[str, Any]]:
        """Return a two-tier :class:`dict` with sections at the first level, and the
        keyv/values at the second level.

        """
        cls = OrderedDict if sort else dict
        secs = cls()
        for sec in sorted(self.sections):
            svs = cls()
            secs[sec] = svs
            opts = self.get_options(sec)
            for k in sorted(opts.keys()):
                svs[k] = opts[k]
        return secs

    def as_flat_dict(self) -> Dict[str, Any]:
        """Return a flat one-tier :class:`dict` with keys in ``<section>:<option>``
        format.

        """
        flat: Dict[str, Any] = {}
        for sec, opts in self.asdict(False).items():
            for k, v in opts.items():
                flat[f'{sec}:{k}'] = v
        return flat

    def asjson(self, *args, sort: bool = True, **kwargs) -> str:
        """Return a JSON string that represents this configuration.  For structure, see
        :meth:`asdict`.

        """
        return json.dumps(self.asdict(sort), *args, **kwargs)

    def _get_short_str(self) -> str:
        sec = self._get_section_short_str()
        return f'{self.__class__.__name__}{{{sec}}}'

    def _raise(self, msg: str, err: Exception = None):
        config_file: Optional[Union[Path, str]] = None
        if hasattr(self, 'config_file'):
            config_file = self.config_file
        if isinstance(config_file, str):
            msg = f'{msg} in file {config_file}'
        elif isinstance(config_file, Path):
            msg = f'{msg} in file {config_file.absolute()}'
        else:
            msg = f'{msg} in {self._get_container_desc()}'
        if err is None:
            raise ConfigurableError(msg)
        else:
            raise ConfigurableError(msg) from err

    def __str__(self):
        return f'<{self._get_short_str()}>'

    def __repr__(self):
        return self.__str__()
