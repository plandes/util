"""Implementation classes that are used as application configuration containers
parsed from files.

"""
__author__ = 'Paul Landes'

from typing import Set, Dict, List, Union
from abc import ABCMeta, abstractmethod
import logging
import os
from io import TextIOBase, StringIO
from pathlib import Path
from copy import deepcopy
from configparser import ConfigParser, ExtendedInterpolation
from ..persist.domain import Primeable
from . import ConfigurableFileNotFoundError, ConfigurableError, Configurable

logger = logging.getLogger(__name__)


class IniConfig(Configurable, Primeable):
    """Application configuration utility.  This reads from a configuration and
    returns sets or subsets of options.

    """
    __slots__ = ('config_file', 'default_section', 'use_interpolation',
                 'nascent', '_cached_sections', '_raw', '_conf')

    def __init__(self,
                 config_file: Union[Path, TextIOBase, Configurable] = None,
                 default_section: str = None,
                 use_interpolation: bool = False,
                 parent: Configurable = None):
        """Create with a configuration file path.

        :param config_file: the configuration file path to read from; if the
                            type is an instance of :class:`io.TextIOBase`, then
                            read it as a file object

        :param default_section: default section (defaults to `default`)

        :param use_interpolation: if ``True``, interpolate variables using
                                  :class:`~configparser.ExtendedInterpolation`

        :param robust: if `True`, then don't raise an error when the
                       configuration file is missing

        """
        super().__init__(default_section, parent=parent)
        if isinstance(config_file, str):
            self.config_file = Path(config_file).expanduser()
        else:
            self.config_file = config_file
        self.use_interpolation = use_interpolation
        self.nascent = deepcopy(self.__dict__)
        self._cached_sections = {}
        self._raw = False
        self._conf = None

    def _create_config_parser(self) -> ConfigParser:
        "Factory method to create the ConfigParser."
        if self.use_interpolation:
            parser = ConfigParser(interpolation=ExtendedInterpolation())
        else:
            parser = ConfigParser()
        return parser

    def _read_config_content(self, cpath: Path, parser: ConfigParser):
        if cpath.is_file():
            with open(cpath) as f:
                parser.read_file(f)
        elif cpath.is_dir():
            writer = StringIO()
            for fpath in cpath.iterdir():
                if fpath.is_file():
                    with open(fpath) as f:
                        writer.write(f.read())
                    writer.write('\n')
            writer.seek(0)
            parser.read_file(writer)

    def _create_and_load_parser_from_file(self, cpath: Path,
                                          parser: ConfigParser):
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'{self.__class__.__name__}: loading config: {cpath}')
        if not cpath.exists():
            raise ConfigurableFileNotFoundError(cpath)
        elif cpath.is_file() or cpath.is_dir():
            self._read_config_content(cpath, parser)
        else:
            raise ConfigurableError(f'Unknown file type: {cpath}')
        return parser

    def _create_and_load_parser(self, parser: ConfigParser):
        if isinstance(self.config_file, (str, Path)):
            self._create_and_load_parser_from_file(self.config_file, parser)
        elif isinstance(self.config_file, TextIOBase):
            writer = self.config_file
            writer.seek(0)
            parser.read_file(writer)
            writer.seek(0)
        elif isinstance(self.config_file, Configurable):
            is_ini = isinstance(self.config_file, IniConfig)
            src: Configurable = self.config_file
            sec: str = None
            if is_ini:
                self.config_file._raw = True
            try:
                for sec in src.sections:
                    parser.add_section(sec)
                    opts = src.get_options(sec)
                    if opts is None:
                        raise ConfigurableError(f'No section: {sec} in {self}')
                    for k, v in opts.items():
                        parser.set(sec, k, v)
            finally:
                if is_ini:
                    self.config_file._raw = False
        elif self.config_file is None:
            pass
        else:
            raise ConfigurableError(
                f'Unknown create type: {type(self.config_file)}')

    @property
    def parser(self) -> ConfigParser:
        """Load the configuration file.

        """
        if self._conf is None:
            parser: ConfigParser = self._create_config_parser()
            self._create_and_load_parser(parser)
            self._conf = parser
        return self._conf

    def _is_initialized(self) -> bool:
        return self._conf is not None

    def reload(self):
        self._conf = None

    def has_option(self, name: str, section: str = None) -> bool:
        section = self.default_section if section is None else section
        conf = self.parser
        if conf.has_section(section):
            return conf.has_option(section, name)
        else:
            return False

    def get_options(self, section: str = None) -> Dict[str, str]:
        opts = None
        section = self.default_section if section is None else section
        conf: ConfigParser = self.parser
        if conf is None:
            if not self.robust:
                raise self._raise('No configuration given')
        elif conf.has_section(section):
            opts = dict(conf.items(section, raw=self._raw))
        if opts is None:
            self._raise(f"No section: '{section}'")
        return opts

    def get_option(self, name: str, section: str = None) -> str:
        opt = None
        section = self.default_section if section is None else section
        conf: ConfigParser = self.parser
        if conf is None:
            if not self.robust:
                self._raise('No configuration given')
        elif conf.has_option(section, name):
            opt = conf.get(section, name, raw=self._raw)
        if opt is None:
            if not conf.has_section(section):
                self._raise(f"No section: '{section}'")
            self._raise(f"No option: '{section}:{name}'")
        return opt

    @property
    def sections(self) -> Set[str]:
        """All sections of the INI file.

        """
        return frozenset(self.parser.sections() or ())

    def _format_option(self, name: str, value: str, section: str) -> str:
        try:
            value = self.serializer.format_option(value)
        except TypeError as e:
            raise ConfigurableError(
                f'Can not serialize {section}:{name}: {e}') from e
        return value

    def set_option(self, name: str, value: str, section: str = None):
        section = self.default_section if section is None else section
        value = self._format_option(name, value, section)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'setting option {name}: {section}:{value}')
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        try:
            self.parser.set(section, name, value)
        except Exception as e:
            raise ConfigurableError(
                f'Cannot set {section}:{name} = {value}: {e}') from e

    def remove_section(self, section: str):
        self.parser.remove_section(section)

    def get_raw_str(self) -> str:
        """"Return the contents of the configuration parser with no interpolated
        values.

        """
        sio = StringIO()
        self.parser.write(sio)
        return sio.getvalue()

    def derive_from_resource(self, path: str, copy_sections=()) -> \
            Configurable:
        """Derive a new configuration from the resource file name ``path``.

        :param path: a resource file (i.e. ``resources/app.conf``)

        :param copy_sections: a list of sections to copy from this to the
                              derived configuration

        """
        kwargs = deepcopy(self.nascent)
        kwargs['config_file'] = path
        conf = self.__class__(**kwargs)
        self.copy_sections(conf, copy_sections)
        return conf

    def prime(self):
        self.parser

    def _get_container_desc(self, include_type: bool = True,
                            max_path_len: int = 3) -> str:
        mod: str = ''
        if isinstance(self.config_file, (str, Path)):
            parts = self.config_file.parts
            path = Path(*parts[max(0, len(parts) - max_path_len):])
            tpe = 'f=' if include_type else ''
            mod = f'{tpe}{path}'
        elif isinstance(self.config_file, Configurable):
            tpe = 'c=' if include_type else ''
            mod = f'{tpe}[{self.config_file}]'
        return mod

    def _get_short_str(self) -> str:
        sec: str = ''
        if self._conf is not None:
            # getting sections invokes parsing, which causes issues if used in
            # a debugging statement when we're not yet ready to parse
            secs = tuple(self.parser.sections())
            if len(secs) > 0:
                sec = secs[0]
        cname: str = self.__class__.__name__
        return f'{cname}({self._get_container_desc()}){{{sec}}}'


class rawconfig(object):
    """Treat all option fetching on ``config`` as raw, or without interpolation.
    This is usually used when ``config`` is the target of section copying with
    :meth:`.Configuration.copy_sections`,

    """
    def __init__(self, config: Configurable):
        self.config = config if isinstance(config, IniConfig) else None

    def __enter__(self):
        if self.config is not None:
            self.config._raw = True

    def __exit__(self, type, value, traceback):
        if self.config is not None:
            self.config._raw = False


class ExtendedInterpolationConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    :class:`~configparser.ExtendedInterpolation`.

    """
    def __init__(self, *args, **kwargs):
        kwargs['use_interpolation'] = True
        super().__init__(*args, **kwargs)


class ExtendedInterpolationEnvConfig(ExtendedInterpolationConfig):
    """An :class:`.IniConfig` implementation that creates a section called
    ``env`` with environment variables passed.

    """

    def __init__(self, *args, remove_vars: List[str] = None,
                 env: dict = None, env_sec: str = 'env', **kwargs):
        self.remove_vars = remove_vars
        if env is None:
            env = {}
            for k, v in os.environ.items():
                env[k] = v.replace('$', '$$')
            self.env = env
        else:
            self.env = env
        self.env_sec = env_sec
        super().__init__(*args, **kwargs)

    def _munge_default_vars(self, vars):
        if vars is not None and self.remove_vars is not None:
            for n in self.remove_vars:
                if n in vars:
                    del vars[n]
        return vars

    def _create_config_parser(self) -> ConfigParser:
        parser = super()._create_config_parser()
        sec = self.env_sec
        parser.add_section(sec)
        for k, v in self.env.items():
            logger.debug(f'adding env section {sec}: {k} -> {v}')
            v = self._format_option(k, v, sec)
            parser.set(sec, k, v)
        return parser


class CommandLineConfig(IniConfig, metaclass=ABCMeta):
    """A configuration object that allows creation by using command line
    arguments as defaults when the configuration file is missing.

    Sub classes must implement the ``set_defaults`` method.  All defaults set
    in this method are then created in the default section of the configuration
    when created with the static method ``from_args``, which is called with the
    parsed command line arguments (usually from some instance or instance of
    subclass :class:`.SimpleActionCli`.

    """
    def set_default(self, name: str, value: str, clobber: bool = None):
        """Set a default value in the ``default`` section of the configuration.

        """
        if clobber is not None:
            self.set_option(name, clobber, self.default_section)
        elif name not in self.options and value is not None:
            self.set_option(name, value, self.default_section)

    @abstractmethod
    def set_defaults(self, *args, **kwargs):
        pass

    @classmethod
    def from_args(cls, config=None, *args, **kwargs):
        if config is None:
            self = cls()
            self._conf = self._create_config_parser()
            self.parser.add_section(self.default_section)
        else:
            self = config
        self.set_defaults(*args, **kwargs)
        return self
