"""Contains a class for importing child configurations.

"""
__author__ = 'Paul Landes'

from typing import Iterable, Tuple, List, Dict, Any
import logging
from itertools import chain
from collections import ChainMap
from io import StringIO, TextIOBase
from pathlib import Path
from configparser import ConfigParser, ExtendedInterpolation
from . import (
    ConfigurableError, Configurable, ConfigurableFactory, IniConfig
)

logger = logging.getLogger(__name__)


class _ParserAdapter(object):
    """Adapts a :class:`~configparser.ConfigParser` to a :class:`.Configurable`.

    """
    def __init__(self, conf: Configurable):
        self.conf = conf

    def get(self, section: str, option: str, *args, **kwags):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f'get ({type(self.conf).__name__}): {section}:{option}')
        return self.conf.get_option(option, section)

    def optionxform(self, option: str) -> str:
        return option.lower()

    def items(self, section: str, raw: bool = False):
        return list(self.conf.get_options(section))

    def __str__(self) -> str:
        return str(self.conf.__class__.__name__)


class _SharedExtendedInterpolation(ExtendedInterpolation):
    """Adds other :class:`Configurable` instances to available parameter to
    substitute.

    """
    def __init__(self, children: Tuple[Configurable], robust: bool = False):
        super().__init__()
        self.children = tuple(map(_ParserAdapter, children))
        self.robust = robust

    def before_get(self, parser: ConfigParser, section: str, option: str,
                   value: str, defaults: ChainMap):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'super: section: {section}:{option}: {value}')
        res = value
        last_ex = None
        parsers = tuple(chain.from_iterable([[parser], self.children]))
        for pa in parsers:
            try:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'inter: {pa}: {section}:{option} = {value}')
                res = super().before_get(pa, section, option, value, defaults)
                last_ex = None
                break
            except Exception as e:
                last_ex = e
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'missing option: {e}')
        if (not self.robust) and (last_ex is not None):
            msg = f'can not set {section}:{option} = {value}: {last_ex}'
            raise ConfigurableError(msg)
        return res


class _StringIniConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    :class:`~configparser.ExtendedInterpolation`.

    """
    def __init__(self, config: TextIOBase, parent: IniConfig,
                 children: Tuple[Configurable]):
        super().__init__(None, parent.default_section)
        self.config = config
        self.children = [parent] + list(children)

    def append_child(self, child: Configurable):
        self.children.append(child)
        for c in self.children:
            c.copy_sections(self)

    def _create_and_load_parser(self) -> ConfigParser:
        parser = ConfigParser(
            defaults=self.create_defaults,
            interpolation=_SharedExtendedInterpolation(self.children))
        parser.read_file(self.config)
        return parser


class ImportIniConfig(IniConfig):
    """A configuration that uses other :class:`.Configurable` classes to load other
    sections.  A special ``config`` section is given that indicates what other
    sections to load as children configuration.  Each of those indicated to
    import are processed in order by:

      1. Creating the delegate child :class:`Configurable` given in the
         section,

      2. Copying all sections from child instance to the parent.

      3. Variable interpolation as a function of
         :class:`~configparser.ConfigParser` using
         :class:`~configparser.ExtendedInterpolation`.

    """
    IMPORT_SECTION = 'import'
    SECTIONS_SECTION = 'sections'
    REFS_SECTION = 'references'

    def __init__(self, *args,
                 config_section: str = IMPORT_SECTION,
                 exclude_config_sections: bool = True,
                 children: Tuple[Configurable] = (),
                 use_interpolation: bool = True,
                 **kwargs):
        """Initialize.

        :param config_file: the configuration file path to read from

        :param default_section: default section (defaults to `default`)

        :param robust: if `True`, then don't raise an error when the
                       configuration file is missing

        :param create_defaults: used to initialize the configuration parser,
                                and useful for when substitution values are
                                baked in to the configuration file

        :param config_section: the name of the section that has the
                               configuration (i.e. the ``sections`` entry)

        :param exclude_config_sections:
             if ``True``, the import and other configuration sections are
             removed

        :param children: additional configurations used both before and after
                         bootstrapping

        """
        super().__init__(*args, **kwargs)
        self.config_section = config_section
        self.exclude_config_sections = exclude_config_sections
        self.children = children
        self.use_interpolation = use_interpolation
        if exclude_config_sections and \
           (self.default_section == self.config_section):
            raise ConfigurableError(
                'you must set exclude_config_sections to False when the ' +
                'import and config section are the same')

    def _get_bootstrap_parser(self) -> _StringIniConfig:
        conf_sec = self.config_section
        parser = IniConfig(self.config_file)
        cparser = parser.parser
        if parser.has_option(self.SECTIONS_SECTION, conf_sec):
            secs = set(parser.get_option_list(self.SECTIONS_SECTION, conf_sec))
            if parser.has_option(self.REFS_SECTION, conf_sec):
                csecs = parser.get_option_list(self.REFS_SECTION, conf_sec)
                secs.update(set(csecs))
            secs.add(conf_sec)
            to_remove = set(parser.sections) - secs
            for r in to_remove:
                cparser.remove_section(r)
        sconf = StringIO()
        cparser.write(sconf)
        sconf.seek(0)
        return _StringIniConfig(sconf, parser, self.children)

    def _create_config(self, section: str, params: Dict[str, Any]) -> \
            Configurable:
        cf = ConfigurableFactory(params)
        class_name = params.get('class_name')
        tpe = params.get('type')
        config_file = params.get('config_file')
        if class_name is not None:
            del params['class_name']
            inst = cf.from_class_name(class_name)
        elif tpe is not None:
            del params['type']
            if tpe is None:
                raise ConfigurableError(
                    f"import section '{section}' has no 'type' parameter")
            inst = cf.from_type(tpe)
        elif config_file is not None:
            del params['config_file']
            inst = cf.from_class_name(Path(config_file))
        return inst

    def _get_children(self) -> Tuple[List[str], Iterable[Configurable]]:
        if not self.config_file.is_file():
            raise ConfigurableError('not a file: {self.config_file}')
        conf_sec: str = self.config_section
        parser: _StringIniConfig = self._get_bootstrap_parser()
        children: List[Configurable] = parser.children
        conf_secs: List[str] = [conf_sec]
        if parser.has_option(self.SECTIONS_SECTION, conf_sec):
            for sec in parser.get_option_list(self.SECTIONS_SECTION, conf_sec):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'populating section {sec}, {children}')
                conf_secs.append(sec)
                params = parser.populate({}, section=sec)
                inst = self._create_config(sec, params)
                parser.append_child(inst)
        return conf_secs, children

    def _create_config_parser(self) -> ConfigParser:
        csecs, children = self._get_children()
        if self.use_interpolation:
            parser = ConfigParser(
                defaults=self.create_defaults,
                interpolation=ExtendedInterpolation())
        else:
            parser = ConfigParser(defaults=self.create_defaults)
        for c in children:
            par_secs = parser.sections()
            for sec in c.sections:
                if sec not in par_secs:
                    parser.add_section(sec)
                for k, v in c.get_options(sec).items():
                    v = self._format_option(k, v, sec)
                    parser.set(sec, k, v)
        if self.exclude_config_sections:
            self._config_sections = csecs
        return parser

    def _create_and_load_parser(self) -> ConfigParser:
        parser = super()._create_and_load_parser()
        if hasattr(self, '_config_sections'):
            for sec in self._config_sections:
                parser.remove_section(sec)
            del self._config_sections
        del self.children
        return parser
