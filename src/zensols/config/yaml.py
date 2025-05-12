"""Application configuration classes parsed from YAML files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Tuple, Set, Any, Union
import logging
from pathlib import Path
from io import TextIOBase, StringIO
import yaml
from yaml.parser import ParserError
from zensols.config import (
    ConfigurableError, ConfigurableFileNotFoundError,
    Configurable, TreeConfigurable
)

logger = logging.getLogger(__name__)


class YamlConfig(TreeConfigurable):
    """Just like :class:`.IniConfig` but parse configuration from YAML files
    using the :mod:`yaml` module.  Variable substitution works just like ini
    files, but you can set what delimiter to use and keys are the paths of the
    data in the hierarchy separated by dots.

    See the test cases for examples.

    """
    CLASS_VER = 0

    def __init__(self, config_file: Union[str, Path, TextIOBase] = None,
                 default_section: str = None,
                 default_vars: Dict[str, Any] = None, delimiter: str = '$',
                 sections_name: str = 'sections', sections: Set[str] = None,
                 parent: Configurable = None):
        """Initialize this instance.  When sections are not set, and the
        sections are not given in configuration file at location
        :obj:`sections_name` the root is made a singleton section.

        :param config_file: the configuration file path to read from; if the
                            type is an instance of :class:`io.TextIOBase`, then
                            read it as a file object

        :param default_vars: used in place of missing variables duing value
                             interpolation; **deprecated**: this will go away in
                             a future release

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`;
                                which defaults to ``defualt``

        :param delimiter: the delimiter used for template replacement with dot
                          syntax, or ``None`` for no template replacement

        :param sections_name: the dot notated path to the variable that has a
                              list of sections

        :param sections: used as the set of sections for this instance

        """
        if isinstance(config_file, str):
            self.config_file = Path(config_file)
        else:
            self.config_file = config_file
        self.delimiter = delimiter
        self._config = None
        super().__init__(default_section=default_section,
                         parent=parent,
                         default_vars=default_vars,
                         sections_name=sections_name,
                         sections=sections)

    def _parse(self) -> Tuple[str, Dict[str, str], Dict[str, str]]:
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'parsing: {self.config_file}')
        cfile = self.config_file
        if isinstance(cfile, Path) and not cfile.is_file():
            raise ConfigurableFileNotFoundError(cfile)
        elif isinstance(cfile, TextIOBase):
            content = cfile.read()
            self.config_file = StringIO(content)
        else:
            with open(cfile) as f:
                content = f.read()
        try:
            struct = yaml.load(content, yaml.FullLoader)
        except ParserError as e:
            raise ConfigurableError(f"Could not parse '{cfile}': {e}") from e
        # struct is None is the file was empty
        if struct is None:
            struct = {}
        context = {}
        context.update(self.default_vars)
        self._flatten(context, '', struct)
        self._all_keys = set(context.keys())
        return content, struct, context

    def _make_class(self) -> type:
        class_name = 'YamlTemplate{}'.format(self.CLASS_VER)
        self.CLASS_VER += 1
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

    def _compile(self) -> Dict[str, Any]:
        content, struct, context = self._parse()
        prev = None
        if self.delimiter is not None:
            cls = self._make_class()
            while prev != content:
                prev = content
                # TODO: raise here for missing keys embedded in the file rather
                # than KeyError
                try:
                    content = cls(content).substitute(context)
                except Exception as e:
                    self._raise('Can not substitute YAML template', e)
        conf: Dict[str, Any] = yaml.load(content, yaml.FullLoader)
        if conf is None:
            conf = {}
        return conf

    def _get_config(self) -> Dict[str, Any]:
        if self._config is None:
            self._config = self._compile()
        return self._config

    def _set_config(self, source: Dict[str, Any]):
        self._config = source
        super().invalidate()
        self.config_file = None
        self._get_config()

    def _is_initialized(self) -> bool:
        return self._config is not None

    def remove_section(self, section: str):
        self._get_config().pop(section, None)
        super().invalidate()
