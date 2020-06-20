"""Implementation classes that are used as application configuration containers
parsed from files.

"""
__author__ = 'Paul Landes'

from abc import ABCMeta, abstractmethod
import os
import sys
from io import TextIOWrapper
import logging
from copy import deepcopy
import configparser
from . import Configurable

logger = logging.getLogger(__name__)


class IniConfig(Configurable):
    """Application configuration utility.  This reads from a configuration and
    returns sets or subsets of options.

    """
    def __init__(self, config_file=None, default_section='default',
                 robust=False, default_vars=None, default_expect=False,
                 create_defaults=None):
        """Create with a configuration file path.

        Keyword arguments:

        :param str config_file: the configuration file path to read from

        :param str default_section: default section (defaults to `default`)

        :param bool robust: if `True`, then don't raise an error when the
                            configuration file is missing

        :param default_expect: if ``True``, raise exceptions when keys and/or
                               sections are not found in the configuration

        :param create_defaults: used to initialize the configuration parser,
                                and useful for when substitution values are
                                baked in to the configuration file
        """

        super().__init__(config_file, default_expect)
        self.default_section = default_section
        self.robust = robust
        self.default_vars = self._munge_default_vars(default_vars)
        self.create_defaults = self._munge_create_defaults(create_defaults)
        self.nascent = deepcopy(self.__dict__)

    def _munge_default_vars(self, vars):
        return vars

    def _munge_create_defaults(self, vars):
        return vars

    def _create_config_parser(self):
        "Factory method to create the ConfigParser."
        return configparser.ConfigParser(defaults=self.create_defaults)

    @property
    def content(self):
        "Return the contents of the configuration file."
        with open(os.path.expanduser(self.config_file)) as f:
            return f.read()

    @property
    def parser(self):
        "Load the configuration file."
        if not hasattr(self, '_conf'):
            cfile = self.config_file
            logger.debug('loading config %s' % cfile)
            if os.path.isfile(cfile):
                conf = self._create_config_parser()
                conf.read(os.path.expanduser(cfile))
            else:
                if self.robust:
                    logger.debug(f'no default config file {cfile}--skipping')
                else:
                    raise IOError(f'no such file: {cfile}')
                conf = None
            self._conf = conf
        return self._conf

    @property
    def file_exists(self):
        return self.parser is not None

    def has_option(self, name, section=None):
        section = self.default_section if section is None else section
        conf = self.parser
        if conf.has_section(section):
            opts = self.get_options(section, opt_keys=[name])
            return opts is not None and name in opts
        else:
            return False

    def get_options(self, section=None, opt_keys=None, vars=None):
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

    def get_option(self, name, section=None, vars=None, expect=None):
        vars = vars if vars else self.default_vars
        if section is None:
            section = self.default_section
        opts = self.get_options(section, opt_keys=[name], vars=vars)
        if opts:
            return opts[name]
        else:
            if self._narrow_expect(expect):
                raise ValueError('no option \'{}\' found in section {}'.
                                 format(name, section))

    @property
    def sections(self):
        """All sections of the INI file.

        """
        secs = self.parser.sections()
        if secs:
            return set(secs)

    def set_option(self, name, value, section=None):
        try:
            value = self.serializer.format_option(value)
        except TypeError as e:
            raise TypeError(f'can not serialize {name}:{section}: {e}')
        logger.debug(f'setting option {name}: {value} in section {section}')
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

    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout):
        """Print a human readable list of sections and options.

        """
        for sec in sorted(self.sections):
            self._write_line(sec, depth, writer)
            for k, v in self.get_options(sec).items():
                self._write_line(f'{k}: {v}', depth + 1, writer)

    def __str__(self):
        return str('file: {}, section: {}'.
                   format(self.config_file, self.sections))

    def __repr__(self):
        return self.__str__()


class ExtendedInterpolationConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    ``configparser.ExtendedInterpolation``.

    """
    def _create_config_parser(self):
        inter = configparser.ExtendedInterpolation()
        return configparser.ConfigParser(
            defaults=self.create_defaults, interpolation=inter)


class ExtendedInterpolationEnvConfig(ExtendedInterpolationConfig):
    """A ``Config`` implementation that creates a section called ``env`` with
    environment variables passed.

    """
    def __init__(self, *args, remove_vars: bool = None,
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

    def _create_config_parser(self):
        parser = super()._create_config_parser()
        sec = self.env_sec
        parser.add_section(sec)
        for k, v in self.env.items():
            logger.debug(f'adding env section {sec}: {k} -> {v}')
            parser.set(sec, k, v)
        # purify for pickle
        del self.env
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
