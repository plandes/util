"""Implementation classes that are used as application configuration containers
parsed from files.

"""
__author__ = 'Paul Landes'

from typing import Set, Dict, List
from abc import ABCMeta, abstractmethod
import logging
import os
from io import StringIO
from pathlib import Path
from copy import deepcopy
from configparser import ConfigParser, ExtendedInterpolation
from . import Configurable

logger = logging.getLogger(__name__)


class IniConfig(Configurable):
    """Application configuration utility.  This reads from a configuration and
    returns sets or subsets of options.

    """
    def __init__(self, config_file: Path = None,
                 default_section: str = 'default', robust: bool = False,
                 default_vars: Dict[any, any] = None,
                 default_expect: bool = False, create_defaults: bool = None):
        """Create with a configuration file path.

        :param config_file: the configuration file path to read from

        :param default_section: default section (defaults to `default`)

        :param default_vars: used use with existing configuration is not found

        :param robust: if `True`, then don't raise an error when the
                       configuration file is missing

        :param default_expect: if ``True``, raise exceptions when keys and/or
                               sections are not found in the configuration

        :param create_defaults: used to initialize the configuration parser,
                                and useful for when substitution values are
                                baked in to the configuration file
        """

        super().__init__(default_expect, default_section)
        if isinstance(config_file, str):
            self.config_file = Path(config_file).expanduser()
        else:
            self.config_file = config_file
        self.robust = robust
        self.default_vars = self._munge_default_vars(default_vars)
        self.create_defaults = self._munge_create_defaults(create_defaults)
        self.nascent = deepcopy(self.__dict__)

    def _munge_default_vars(self, vars):
        return vars

    def _munge_create_defaults(self, vars):
        return vars

    def _create_config_parser(self) -> ConfigParser:
        "Factory method to create the ConfigParser."
        return ConfigParser(defaults=self.create_defaults)

    @property
    def parser(self):
        """Load the configuration file.

        """
        if not hasattr(self, '_conf'):
            cpath = self.config_file
            logger.debug(f'loading config {cpath}')
            if not cpath.exists():
                if self.robust:
                    logger.debug(f'no default config file {cpath}--skipping')
                else:
                    raise IOError(f'no such file: {cpath}')
                self._conf = None
            elif cpath.is_file():
                self._conf = self._create_config_parser()
                self._conf.read(cpath)
            elif cpath.is_dir():
                agg = StringIO()
                for fpath in cpath.iterdir():
                    if fpath.is_file():
                        with open(fpath) as f:
                            agg.write(f.read())
                        agg.write('\n')
                self._conf = self._create_config_parser()
                agg.seek(0)
                self._conf.read_file(agg)
            else:
                raise OSError(f'unknown file type: {cpath}')
        return self._conf

    def reload(self):
        if hasattr(self, '_conf'):
            del self._conf

    def has_option(self, name: str, section: str = None) -> bool:
        section = self.default_section if section is None else section
        conf = self.parser
        if conf.has_section(section):
            opts = self.get_options(section, opt_keys=[name])
            return opts is not None and name in opts
        else:
            return False

    def get_options(self, section: str = None, opt_keys: Set[str] = None,
                    vars: Dict[str, str] = None) -> Dict[str, str]:
        section = self.default_section if section is None else section
        vars = vars if vars else self.default_vars
        conf = self.parser
        opts = {}
        if opt_keys is None:
            if conf is None:
                opt_keys = {}
            else:
                if not self.robust or conf.has_section(section):
                    opt_keys = conf.options(section)
                else:
                    opt_keys = {}
        else:
            logger.debug('conf: %s' % conf)
            copts = conf.options(section) if conf else {}
            opt_keys = set(opt_keys).intersection(set(copts))
        for option in opt_keys:
            logger.debug(f'option: {option}, vars: {vars}')
            opts[option] = conf.get(section, option, vars=vars)
        return opts

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
            raise TypeError(f'can not serialize {section}:{name}: {e}')
        return value

    def set_option(self, name, value, section=None):
        section = self.default_section if section is None else section
        value = self._format_option(name, value, section)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'setting option {name}: {section}:{value}')
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, name, value)

    def derive_from_resource(self, path: str, copy_sections=()) -> Configurable:
        """Derive a new configuration from the resource file name ``path``.

        :param path: a resource file (i.e. ``resources/app.conf``)
        :pram copy_sections: a list of sections to copy from this to the
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
    ``configparser.ExtendedInterpolation``.

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
        if 'default_expect' not in kwargs:
            kwargs['default_expect'] = True
        self.remove_vars = remove_vars
        if env is None:
            self.env = os.environ
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
    subclass ``SimpleActionCli``.

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
