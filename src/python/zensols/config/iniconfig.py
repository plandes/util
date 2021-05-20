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
from . import ConfigurableFileNotFoundError, ConfigurableError, Configurable

logger = logging.getLogger(__name__)


class IniConfig(Configurable):
    """Application configuration utility.  This reads from a configuration and
    returns sets or subsets of options.

    """
    def __init__(self, config_file: Union[Path, TextIOBase] = None,
                 default_section: str = None,
                 create_defaults: bool = None):
        """Create with a configuration file path.

        :param config_file: the configuration file path to read from; if the
                            type is an instance of :class:`io.TextIOBase`, then
                            read it as a file object

        :param default_section: default section (defaults to `default`)

        :param robust: if `True`, then don't raise an error when the
                       configuration file is missing

        :param create_defaults: used to initialize the configuration parser,
                                and useful for when substitution values are
                                baked in to the configuration file

        """

        super().__init__(default_section)
        if isinstance(config_file, str):
            self.config_file = Path(config_file).expanduser()
        else:
            self.config_file = config_file
        self.create_defaults = self._munge_create_defaults(create_defaults)
        self.nascent = deepcopy(self.__dict__)
        self._cached_sections = {}

    def _munge_create_defaults(self, vars):
        return vars

    def _create_config_parser(self) -> ConfigParser:
        "Factory method to create the ConfigParser."
        return ConfigParser(defaults=self.create_defaults)

    def _read_config_content(self, cpath: Path, writer: TextIOBase):
        if cpath.is_file():
            with open(cpath) as f:
                writer.write(f.read())
        elif cpath.is_dir():
            for fpath in cpath.iterdir():
                if fpath.is_file():
                    with open(fpath) as f:
                        writer.write(f.read())
                    writer.write('\n')
            self._conf = self._create_config_parser()
            writer.seek(0)
            self._conf.read_file(writer)

    def _create_and_load_parser(self) -> ConfigParser:
        if isinstance(self.config_file, TextIOBase):
            writer = self.config_file
            writer.seek(0)
            parser = self._create_config_parser()
            parser.read_file(writer)
            return parser
        else:
            return self._create_and_load_parser_from_file(self.config_file)

    def _create_and_load_parser_from_file(self, cpath: Path) -> ConfigParser:
        logger.debug(f'loading config {cpath}')
        if not cpath.exists():
            raise ConfigurableFileNotFoundError(cpath)
        elif cpath.is_file() or cpath.is_dir():
            writer = StringIO()
            self._read_config_content(cpath, writer)
            writer.seek(0)
            parser = self._create_config_parser()
            parser.read_file(writer)
        else:
            raise ConfigurableError(f'Unknown file type: {cpath}')
        return parser

    @property
    def parser(self) -> ConfigParser:
        """Load the configuration file.

        """
        if not hasattr(self, '_conf'):
            self._conf = self._create_and_load_parser()
        return self._conf

    def reload(self):
        if hasattr(self, '_conf'):
            del self._conf

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
                raise ConfigurableError('No configuration given')
        elif conf.has_section(section):
            opts = {k: conf.get(section, k) for k in conf.options(section)}
        if opts is None:
            raise ConfigurableError(f'No section: {section}')
        return opts

    def get_option(self, name: str, section: str = None) -> str:
        opt = None
        section = self.default_section if section is None else section
        conf: ConfigParser = self.parser
        if conf is None:
            if not self.robust:
                raise ConfigurableError('No configuration given')
        elif conf.has_option(section, name):
            opt = conf.get(section, name)
        if opt is None:
            if not conf.has_section(section):
                raise ConfigurableError(f'No section: {section}')
            raise ConfigurableError(f'No option: {section}:{name}')
        return opt

    @property
    def sections(self) -> Set[str]:
        """All sections of the INI file.

        """
        secs = self.parser.sections()
        if secs:
            return set(secs)

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
        self.parser.set(section, name, value)

    def remove_section(self, section: str):
        self.parser.remove_section(section)

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

    def __str__(self):
        return f'file: {self.config_file}, section: {self.sections}'

    def __repr__(self):
        return self.__str__()


class ExtendedInterpolationConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    :class:`~configparser.ExtendedInterpolation`.

    """
    def _create_config_parser(self) -> ConfigParser:
        inter = ExtendedInterpolation()
        return ConfigParser(defaults=self.create_defaults, interpolation=inter)


class ExtendedInterpolationEnvConfig(ExtendedInterpolationConfig):
    """An :class:`.IniConfig` implementation that creates a section called ``env``
    with environment variables passed.

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
    """A configuration object that allows creation by using command line arguments
    as defaults when the configuration file is missing.

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
