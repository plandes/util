"""Classes that are used as application configuration containers parsed from
files.

"""
__author__ = 'Paul Landes'


from typing import Union, Dict, Any
from abc import ABCMeta, abstractmethod, ABC
import os
import sys
from io import TextIOWrapper
import logging
from pprint import pprint
from copy import deepcopy
import re
import json
import configparser
from pathlib import Path
import inspect
import pkg_resources

logger = logging.getLogger(__name__)


class Writable(ABC):
    """An interface for classes that have multi-line debuging capability.

    """
    def _sp(self, depth: int):
        """Utility method to create a space string.

        """
        indent = getattr(self, '_indent', 4)
        return ' ' * (depth * indent)

    def _write_line(self, line: str, depth: int = 0,
                    writer: TextIOWrapper = sys.stdout):
        """Write a line of text ``line`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        writer.write(f'{self._sp(depth)}{line}\n')

    def _write_dict(self, data: dict, depth: int = 0,
                    writer: TextIOWrapper = sys.stdout):
        """Write dictionary ``data`` with the correct indentation per ``depth`` to
        ``writer``.

        """
        sp = self._sp(depth)
        for k, v in data.items():
            writer.write(f'{sp}{k}: {v}\n')

    @abstractmethod
    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention ``depth``.

        """
        pass


class Settings(object):
    """A default object used to populate in ``Configurable.populate``.

    """
    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()

    def write(self, writer=sys.stdout):
        pprint(self.__dict__, writer)


class Configurable(Writable, metaclass=ABCMeta):
    """An abstract base class that represents an application specific
    configuration.

    """
    FLOAT_REGEXP = re.compile(r'^[-+]?\d*\.\d+$')
    INT_REGEXP = re.compile(r'^[-+]?[0-9]+$')
    BOOL_REGEXP = re.compile(r'^True|False')
    PATH_REGEXP = re.compile(r'^path:\s*(.+)$')
    EVAL_REGEXP = re.compile(r'^eval(?:\((.+)\))?:\s*(.+)$', re.DOTALL)
    JSON_REGEXP = re.compile(r'^json:\s*(.+)$', re.DOTALL)
    PRIMITIVES = set([bool, float, int, None.__class__])

    def __init__(self, config_file, default_expect):
        self.config_file = config_file
        self.default_expect = default_expect

    def _narrow_expect(self, expect):
        if expect is None:
            expect = self.default_expect
        return expect

    @abstractmethod
    def get_option(self, name, section=None, vars=None, expect=None):
        """Return an option from ``section`` with ``name``.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        pass

    @abstractmethod
    def get_options(self, section='default', opt_keys=None, vars=None):
        """Get all options for a section.  If ``opt_keys`` is given return only
        options with those keys.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        pass

    @abstractmethod
    def has_option(self, name, section=None):
        pass

    def get_option_list(self, name, section=None, vars=None,
                        expect=None, separator=','):
        """Just like :py:meth:`get_option` but parse as a list using ``split``.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        val = self.get_option(name, section, vars, expect)
        return val.split(separator) if val else []

    def get_option_boolean(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as a boolean (any case `true`).

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        val = self.get_option(name, section, vars, expect)
        val = val.lower() if val else 'false'
        return val == 'true'

    def get_option_int(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as an integer.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        val = self.get_option(name, section, vars, expect)
        if val:
            return int(val)

    def get_option_float(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as a float.

        """
        val = self.get_option(name, section, vars, expect)
        if val:
            return float(val)

    def get_option_path(self, name, section=None, vars=None,
                        expect=None, create=None):
        """Just like :py:meth:`get_option` but return a ``pathlib.Path`` object of the
        string.

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

    def get_option_object(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as an object per object syntax
        rules.

        :see: :py:meth:`.parse_object`

        """
        val = self.get_option(name, section, vars, expect)
        if val:
            return self.parse_object(val)

    @property
    def options(self):
        """Return all options from the default section.

        """
        return self.get_options()

    def _parse_eval(self, pconfig: str, evalstr: str = None) -> str:
        if pconfig is not None:
            pconfig = eval(pconfig)
            if 'import' in pconfig:
                imports = pconfig['import']
                logger.debug(f'imports: {imports}')
                for i in imports:
                    logger.debug(f'importing: {i}')
                    exec(f'import {i}')
        if evalstr is not None:
            return eval(evalstr)

    def parse_object(self, v: str) -> Any:
        """Parse as a string in to a Python object.  The following is done to parse the
        string in order:

          1. Primitive (i.e. ``1.23`` is a float, ``True`` is a boolean)
          2. A :class:`pathlib.Path` object when prefixed with ``path:``.
          3. Evaluate using the Python parser when prefixed ``eval:``.
          4. Evaluate as JSON when prefixed with ``json:``.

        """
        if v == 'None':
            v = None
        elif self.FLOAT_REGEXP.match(v):
            v = float(v)
        elif self.INT_REGEXP.match(v):
            v = int(v)
        elif self.BOOL_REGEXP.match(v):
            v = v == 'True'
        else:
            parsed = None
            m = self.PATH_REGEXP.match(v)
            if m:
                parsed = Path(m.group(1))
            if parsed is None:
                m = self.EVAL_REGEXP.match(v)
                if m:
                    pconfig, evalstr = m.groups()
                    parsed = self._parse_eval(pconfig, evalstr)
            if parsed is None:
                m = self.JSON_REGEXP.match(v)
                if m:
                    parsed = json.loads(m.group(1))
            if parsed is not None:
                v = parsed
        return v

    def populate_state(self, state: Dict[str, str],
                       obj: Union[dict, object] = None,
                       parse_types: bool = True) -> Union[dict, object]:
        """Populate an object with at string dictionary.  The keys are used for the
        output, and the values are parsed in to Python objects using
        :py:meth:`.parse_object`.  The keys in the input are used as the same
        keys if ``obj`` is a ``dict``.  Otherwise, set data as attributes on
        the object with :py:func:`setattr`.

        :param state: the data to parse

        :param obj: the object to populate

        """
        obj = Settings() if obj is None else obj
        is_dict = isinstance(obj, dict)
        for k, v in state.items():
            if parse_types and isinstance(v, str):
                v = self.parse_object(v)
            logger.debug('setting {} => {} on {}'.format(k, v, obj))
            if is_dict:
                obj[k] = v
            else:
                setattr(obj, k, v)
        return obj

    def populate(self, obj=None, section=None, parse_types=True):
        """Set attributes in ``obj`` with ``setattr`` from the all values in
        ``section``.

        """
        section = self.default_section if section is None else section
        sec = self.get_options(section)
        return self.populate_state(sec, obj, parse_types)

    def format_option(self, obj: Any) -> str:
        """Format a Python object in to the string represetation per object syntax
        rules.

        :see: :py:meth:`.parse_object`

        """
        v = None
        cls = obj.__class__
        if cls == str:
            v = obj
        elif cls in self.PRIMITIVES:
            v = str(obj)
        elif isinstance(obj, Path):
            return f'path: {obj}'
        elif isinstance(obj, set):
            raise ValueError('to implement')
        else:
            v = 'json: ' + json.dumps(obj)
        return v

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
        "Return all sections."
        secs = self.parser.sections()
        if secs:
            return set(secs)

    def set_option(self, name, value, section=None):
        try:
            value = self.format_option(value)
        except TypeError as e:
            raise TypeError(f'can not serialize {name}:{section}: {e}')
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
