import os
import sys
import logging
from abc import ABCMeta, abstractmethod
from copy import deepcopy
import re
import configparser
from pathlib import Path
import inspect
import pkg_resources

logger = logging.getLogger(__name__)


class Settings(object):
    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()

    def pprint(self):
        from pprint import pprint
        pprint(self.__dict__)


class Configurable(object):
    FLOAT_REGEXP = re.compile(r'^[-+]?\d*\.\d+$')
    INT_REGEXP = re.compile(r'^[-+]?[0-9]+$')
    BOOL_REGEXP = re.compile(r'^True|False')
    EVAL_REGEXP = re.compile(r'^eval:\s*(.+)$')

    def __init__(self, config_file, default_expect):
        self.config_file = config_file
        self.default_expect = default_expect

    def _narrow_expect(self, expect):
        if expect is None:
            expect = self.default_expect
        return expect

    def get_option(self, name, expect=None):
        raise ValueError('get_option is not implemented')

    def get_options(self, name, expect=None):
        raise ValueError('get_options is not implemented')

    @property
    def options(self):
        raise ValueError('get_option is not implemented')

    def populate(self, obj=None, section=None, parse_types=True):
        """Set attributes in ``obj`` with ``setattr`` from the all values in
        ``section``.

        """
        section = self.default_section if section is None else section
        obj = Settings() if obj is None else obj
        is_dict = isinstance(obj, dict)
        for k, v in self.get_options(section).items():
            if parse_types:
                if v == 'None':
                    v = None
                elif self.FLOAT_REGEXP.match(v):
                    v = float(v)
                elif self.INT_REGEXP.match(v):
                    v = int(v)
                elif self.BOOL_REGEXP.match(v):
                    v = v == 'True'
                else:
                    m = self.EVAL_REGEXP.match(v)
                    if m:
                        evalstr = m.group(1)
                        v = eval(evalstr)
            logger.debug('setting {} => {} on {}'.format(k, v, obj))
            if is_dict:
                obj[k] = v
            else:
                setattr(obj, k, v)
        return obj

    def _get_calling_module(self):
        """Get the last module in the call stack that is not this module or ``None`` if
        the call originated from this module.

        """
        for frame in inspect.stack():
            mod = inspect.getmodule(frame[0])
            logger.debug(f'calling module: {mod}')
            if mod is not None:
                mod_name = mod.__name__
                if mod_name != __name__:
                    return mod

    def resource_filename(self, resource_name, module_name=None):
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
                mod_name = mod.__name__
        if module_name is None:
            module_name = __name__
        if pkg_resources.resource_exists(mod_name, resource_name):
            res = pkg_resources.resource_filename(mod_name, resource_name)
        else:
            res = resource_name
        return Path(res)


class Config(Configurable):
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

        super(Config, self).__init__(config_file, default_expect)
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

    def get_options(self, section='default', opt_keys=None, vars=None):
        """
        Get all options for a section.  If ``opt_keys`` is given return
        only options with those keys.
        """
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
        """Return an option from ``section`` with ``name``.

        :param section: section in the ini file to fetch the value; defaults to
        constructor's ``default_section``

        """
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

    def get_option_list(self, name, section=None, vars=None,
                        expect=None, separator=','):
        """Just like ``get_option`` but parse as a list using ``split``.

        """
        val = self.get_option(name, section, vars, expect)
        return val.split(separator) if val else []

    def get_option_boolean(self, name, section=None, vars=None, expect=None):
        """Just like ``get_option`` but parse as a boolean (any case `true`).

        """
        val = self.get_option(name, section, vars, expect)
        val = val.lower() if val else 'false'
        return val == 'true'

    def get_option_int(self, name, section=None, vars=None, expect=None):
        """Just like ``get_option`` but parse as an integer."""
        val = self.get_option(name, section, vars, expect)
        if val:
            return int(val)

    def get_option_float(self, name, section=None, vars=None, expect=None):
        """Just like ``get_option`` but parse as a float."""
        val = self.get_option(name, section, vars, expect)
        if val:
            return float(val)

    def get_option_path(self, name, section=None, vars=None,
                        expect=None, create=None):
        """Just like ``get_option`` but return a ``pathlib.Path`` object of
        the string.

        :param create: if ``parent`` then create the path and all parents not
                       including the file; if ``dir``, then create all parents;
                       otherwise do not create anything

        """
        val = self.get_option(name, section, vars, expect)
        path = None
        if val is not None:
            path = Path(val)
            if create == 'dir':
                path.mkdir(parents=True, exist_ok=True)
            if create == 'file':
                path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def options(self):
        "Return all options from the default section."
        return self.get_options()

    @property
    def sections(self):
        "Return all sections."
        secs = self.parser.sections()
        if secs:
            return set(secs)

    def set_option(self, name, value, section=None):
        logger.debug(f'setting option {name}: {value} in section {section}')
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, name, value)

    def copy_sections(self, to_populate: Configurable, sections: list):
        for sec in sections:
            for k, v in self.get_options(sec).items():
                to_populate.set_option(k, v, sec)

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

    def pprint(self, writer=sys.stdout):
        """Print a human readable list of sections and options.

        """
        for sec in self.sections:
            writer.write(f'{sec}:\n')
            for k, v in self.get_options(sec).items():
                writer.write(f'  {k}: {v}\n')

    def __str__(self):
        return str('file: {}, section: {}'.
                   format(self.config_file, self.sections))

    def __repr__(self):
        return self.__str__()


class ExtendedInterpolationConfig(Config):
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
        super(ExtendedInterpolationEnvConfig, self).__init__(*args, **kwargs)

    def _munge_default_vars(self, vars):
        if vars is not None and self.remove_vars is not None:
            for n in self.remove_vars:
                if n in vars:
                    del vars[n]
        return vars

    def _create_config_parser(self):
        parser = super(ExtendedInterpolationEnvConfig, self)._create_config_parser()
        sec = self.env_sec
        parser.add_section(sec)
        for k, v in self.env.items():
            logger.debug(f'adding env section {sec}: {k} -> {v}')
            parser.set(sec, k, v)
        # purify for pickle
        del self.env
        return parser


class CommandLineConfig(Config, metaclass=ABCMeta):
    """A configuration object that allows creation by using command line arguments
    as defaults when the configuration file is missing.

    Sub classes must implement the ``set_defaults`` method.  All defaults set
    in this method are then created in the default section of the configuration
    when created with the static method ``from_args``, which is called with the
    parsed command line arguments (usually from some instance or instance of
    subclass ``SimpleActionCli``.

    """
    def __init__(self, *args, **kwargs):
        super(CommandLineConfig, self).__init__(*args, **kwargs)

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
