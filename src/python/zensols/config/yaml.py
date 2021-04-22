"""Application configuration classes parsed from YAML files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Tuple, Set, Any, Union
import logging
from pathlib import Path
from io import TextIOBase
import copy
import yaml
from zensols.config import ConfigurableError, Configurable, Dictable

logger = logging.getLogger(__name__)


class YamlConfig(Configurable, Dictable):
    """Just like :class:`.IniConfig` but parse configuration from YAML files.
    Variable substitution works just like ini files, but you can set what
    delimiter to use and keys are the paths of the data in the hierarchy
    separated by dots.

    See the test cases for example.

    """
    CLASS_VER = 0

    def __init__(self, config_file: Union[Path, TextIOBase] = None,
                 default_section: str = None, default_vars: str = None,
                 delimiter: str = '$', sections_name: str = 'sections'):
        """Initialize this instance.

        :param config_file: the configuration file path to read from; if the
                            type is an instance of :class:`io.TextIOBase`, then
                            read it as a file object

        :param default_section: default section (defaults to `default`)

        """
        super().__init__(default_section)
        self.config_file = config_file
        self.default_vars = default_vars if default_vars else {}
        self.delimiter = delimiter
        self.sections_name = sections_name

    @classmethod
    def _is_primitive(cls, obj) -> bool:
        return isinstance(obj, str) or \
           isinstance(obj, list) or \
           isinstance(obj, bool)

    def _parse(self) -> Tuple[str, Dict[str, str], Dict[str, str]]:
        def flatten(path, n):
            logger.debug('path: {}, n: <{}>'.format(path, n))
            logger.debug('context: <{}>'.format(context))
            if n is None:
                context[path] = None
            elif self._is_primitive(n):
                context[path] = n
            elif isinstance(n, dict):
                for k, v in n.items():
                    k = path + '.' + k if len(path) else k
                    flatten(k, v)
            else:
                raise ConfigurableError(f'Unknown yaml type {type(n)}: {n}')

        if isinstance(self.config_file, TextIOBase):
            content = self.config_file
        else:
            with open(self.config_file) as f:
                content = f.read()
        struct = yaml.load(content, yaml.FullLoader)
        context = {}
        context.update(self.default_vars)
        flatten('', struct)
        self._all_keys = copy.copy(list(context.keys()))
        return content, struct, context

    def _make_class(self) -> type:
        class_name = 'YamlTemplate{}'.format(self.CLASS_VER)
        self.CLASS_VER += 1
        # why couldn't they have made idpattern and delimiter instance members?
        # note we have to give the option of different delimiters since the
        # default '$$' (use case=OS env vars) is always resolved to '$' given
        # the iterative variable substitution method
        #
        # Yes, this really is necessary.  From the string.Template
        # documentation: Advanced usage: you can derive subclasses of Template
        # to customize the placeholder syntax, delimiter character, or the
        # entire regular expression used to parse template strings. To do this,
        # you can override these class attributes:
        code = """\
from string import Template
class """ + class_name + """(Template):
     idpattern = r'[a-z][_a-z0-9.]*'
     delimiter = '""" + self.delimiter + '\''
        exec(code)
        cls = eval(class_name)
        return cls

    def _compile(self) -> Dict[str, str]:
        content, struct, context = self._parse()
        prev = None
        cls = self._make_class()
        while prev != content:
            prev = content
            # TODO: raise here for missing keys embedded in the file rather
            # than KeyError
            content = cls(content).substitute(context)
        return yaml.load(content, yaml.FullLoader)

    @property
    def config(self) -> Dict[str, Any]:
        if not hasattr(self, '_config'):
            self._config = self._compile()
        return self._config

    def _from_dictable(self, recurse: bool, readable: bool,
                       class_name_param: str = None) -> Dict[str, Any]:
        return self.config

    def get_tree(self, name) -> Dict[str, Any]:
        def find(n, path, name):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'search: n={n}, path={path}, name={name}')
            if path == name:
                logger.debug(f'found: <{n}>')
                return n
            elif isinstance(n, dict):
                for k, v in n.items():
                    k = path + '.' + k if len(path) else k
                    v = find(v, k, name)
                    if v is not None:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'found {name} -> {v}')
                        return v
                logger.debug('not found: {}'.format(name))
        return find(self.config, '', name)

    def _get_option(self, name: str) -> str:
        node = self.get_tree(name)
        if self._is_primitive(node):
            return node
        elif self.default_vars is not None and name in self.default_vars:
            return self.default_vars[name]
        else:
            raise ConfigurableError('No such option: {}'.format(name))

    def set_option(self, name: str, value: str, section: str = None):
        """This is a no-op for now as client's don't expect an exception."""
        # TODO: implement
        pass

    @property
    def options(self) -> Dict[str, Any]:
        if not hasattr(self, '_options'):
            self.config
            self._options = {}
            for k in self._all_keys:
                self._options[k] = self._get_option(k)
        return self._options

    def reload(self):
        if hasattr(self, '_options'):
            del self._options
            del self._all_keys

    def has_option(self, name: str):
        opts = self.options
        return name in opts

    def get_option(self, name: str, section: str = None) -> str:
        """Return an option using a dot encoded path.

        """
        if self.default_vars and name in self.default_vars:
            return self.default_vars[name]
        else:
            ops = self.options
            if name in ops:
                return ops[name]
            else:
                raise ConfigurableError(f'No such option: {name}')

    def get_options(self, name: str = None) -> Dict[str, str]:
        name = self.default_section if name is None else name
        if self.default_vars and name in self.default_vars:
            return self.default_vars[name]
        else:
            node = self.get_tree(name)
            if not isinstance(node, str) or isinstance(node, list):
                return node
            elif name in self.default_vars:
                return self.default_vars[name]
            else:
                raise ConfigurableError(f'No such option: {name}')

    @property
    def root(self) -> str:
        """Return the (first) root name of the Yaml configuration file.

        """
        if not hasattr(self, '_root'):
            root_keys = self.config.keys()
            self._root = next(iter(root_keys))
        return self._root

    @property
    def sections(self) -> Set[str]:
        """Return the sections by finding the :obj:`section_name` based from the
        :obj:`root`.

        """
        sec_key = f'{self.root}.{self.sections_name}'
        if self.has_option(sec_key):
            return tuple(self.get_option_list(sec_key))
