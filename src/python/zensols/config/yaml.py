"""Application configuration classes parsed from YAML files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Tuple, Set, Any
import logging
import sys
from pathlib import Path
from pprint import pprint
import copy
import yaml
from zensols.config import Configurable

logger = logging.getLogger(__name__)


class YamlConfig(Configurable):
    """Just like zensols.actioncli.Config but parse configuration from YAML files.
    Variable substitution works just like ini files, but you can set what
    delimiter to use and keys are the paths of the data in the hierarchy
    separated by dots.

    See the test cases for example.

    """
    CLASS_VER = 0

    def __init__(self, config_file: Path = None,
                 default_section: str = 'default', default_vars: str = None,
                 delimiter: str = '$', default_expect: bool = False,
                 sections_name: str = 'sections'):
        """Initialize this instance.

        :param config_file: the ``.yml`` configuration file path to read from

        :param default_section: default section (defaults to `default`)

        :param default_vars: used use with existing configuration is not found

        

        :param default_expect: if ``True``, raise exceptions when keys and/or
                               sections are not found in the configuration

        """
        super().__init__(default_expect, default_section)
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
        with open(self.config_file) as f:
            content = f.read()
        struct = yaml.load(content, yaml.FullLoader)
        context = {}
        context.update(self.default_vars)

        def flatten(path, n):
            logger.debug('path: {}, n: <{}>'.format(path, n))
            logger.debug('context: <{}>'.format(context))
            if self._is_primitive(n):
                context[path] = n
            else:
                if isinstance(n, dict):
                    for k, v in n.items():
                        k = path + '.' + k if len(path) else k
                        flatten(k, v)
                else:
                    raise ValueError('unknown yaml type {}: {}'.
                                     format(type(n), n))

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

    def write(self, writer=sys.stdout):
        pprint(self.config, writer)

    def _option(self, name):
        def find(n, path, name):
            logger.debug(
                'search: n={}, path={}, name={}'.format(n, path, name))
            if path == name:
                logger.debug('found: <{}>'.format(n))
                return n
            elif isinstance(n, dict):
                for k, v in n.items():
                    k = path + '.' + k if len(path) else k
                    v = find(v, k, name)
                    if v is not None:
                        logger.debug('found {} -> {}'.format(name, v))
                        return v
                logger.debug('not found: {}'.format(name))
        return find(self.config, '', name)

    def _get_option(self, name, expect=None):
        node = self._option(name)
        if self._is_primitive(node):
            return node
        elif self.default_vars is not None and name in self.default_vars:
            return self.default_vars[name]
        elif self._narrow_expect(expect):
            raise ValueError('no such option: {}'.format(name))

    @property
    def options(self):
        if not hasattr(self, '_options'):
            self.config
            self._options = {}
            for k in self._all_keys:
                self._options[k] = self._get_option(k, expect=True)
        return self._options

    def reload(self):
        if hasattr(self, '_options'):
            del self._options
            del self._all_keys

    def has_option(self, name):
        opts = self.options
        return name in opts

    def get_option(self, name, section=None, vars=None, expect=None) -> str:
        """Return an option using a dot encoded path.

        """
        if self.default_vars and name in self.default_vars:
            return self.default_vars[name]
        else:
            ops = self.options
            if name in ops:
                return ops[name]
            elif self._narrow_expect(expect):
                raise ValueError('no such option: {}'.format(name))

    def get_options(self, name='default', opt_keys=None, vars=None,
                    expect=None) -> Dict[str, str]:
        if self.default_vars and name in self.default_vars:
            return self.default_vars[name]
        else:
            node = self._option(name)
            if not isinstance(node, str) or isinstance(node, list):
                return node
            elif name in self.default_vars:
                return self.default_vars[name]
            elif self._narrow_expect(expect):
                raise ValueError('no such option: {}'.format(name))

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
