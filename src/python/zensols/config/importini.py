"""Contains a class for importing child configurations.

"""
__author__ = 'Paul Landes'

from typing import Iterable, Tuple, List
import logging
import sys
from io import StringIO
from itertools import chain
from collections import ChainMap
from configparser import (
    ConfigParser, ExtendedInterpolation,
    InterpolationMissingOptionError)
from . import Configurable, IniConfig, ClassImporter

logger = logging.getLogger(__name__)


class _ParserAdapter(object):
    def __init__(self, conf: Configurable):
        self.conf = conf

    def get(self, section: str, option: str, *args, **kwags):
        return self.conf.get_option(option, section)

    def optionxform(self, option: str) -> str:
        return option.lower()

    def items(self, section: str, raw: bool = False):
        return list(self.conf.get_options(section))


class _SharedExtendedInterpolation(ExtendedInterpolation):
    """Adds other :class:`Configurable` instances to available parameter to
    substitute.

    """
    def __init__(self, children: Tuple[Configurable], robust: bool = False):
        super().__init__()
        self.children = map(_ParserAdapter, children)
        self.robust = robust

    def before_get(self, parser: ConfigParser, section: str, option: str,
                   value: str, defaults: ChainMap):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'super: section: {section}:{option}: {value}')
        res = value
        last_ex = None
        parsers = chain.from_iterable([[parser], self.children])
        for pa in parsers:
            try:
                res = super().before_get(pa, section, option, value, defaults)
                break
            except InterpolationMissingOptionError as e:
                last_ex = e
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'missing option: {e}')
        if (res is None) and (not self.robust) and (last_ex is not None):
            raise last_ex
        return res


class _StringIniConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    :class:`~configparser.ExtendedInterpolation`.

    """
    def __init__(self, config: str, parent: IniConfig):
        super().__init__(
            parent.default_expect, parent.default_section, parent.default_vars)
        self.config = config
        self.children = [parent]

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
    def __init__(self, *args,
                 config_section: str = 'config',
                 exclude_config_sections: bool = False,
                 **kwargs):
        if 'default_expect' not in kwargs:
            kwargs['default_expect'] = True
        super().__init__(*args, **kwargs)
        self.config_section = config_section
        self.exclude_config_sections = exclude_config_sections

    def _mod_name(self) -> str:
        mname = sys.modules[__name__].__name__
        parts = mname.split('.')
        if len(parts) > 1:
            mname = '.'.join(parts[:-1])
        return mname

    def _get_bootstrap_parser(self):
        conf_sec = self.config_section
        parser = IniConfig(self.config_file, default_expect=True)
        secs = set(parser.get_option_list('imports', conf_sec))
        if parser.has_option('sections', conf_sec):
            csecs = parser.get_option_list('sections', conf_sec)
            secs.update(set(csecs))
        secs.add(conf_sec)
        to_remove = set(parser.sections) - secs
        cparser = parser.parser
        for r in to_remove:
            cparser.remove_section(r)
        sconf = StringIO()
        cparser.write(sconf)
        sconf.seek(0)
        return _StringIniConfig(sconf, parser)

    def _get_children(self) -> Iterable[Configurable]:
        if not self.config_file.is_file():
            raise ValueError('not a file: {self.config_file}')
        mod_name = self._mod_name()
        conf_sec = self.config_section
        parser = self._get_bootstrap_parser()
        children: List[Configurable] = parser.children
        conf_secs = [conf_sec]
        for sec in parser.get_option_list('imports', conf_sec):
            #print(f'populating section {sec}, {children}')
            conf_secs.append(sec)
            params = parser.populate(section=sec).asdict()
            class_name = params.get('class_name')
            if class_name is None:
                tpe = params['type']
                del params['type']
                class_name = f'{mod_name}.{tpe.capitalize()}Config'
            else:
                del params['class_name']
            inst = ClassImporter(class_name, False).instance(**params)
            children.append(inst)
        return conf_secs, children

    def _create_config_parser(self) -> ConfigParser:
        csecs, children = self._get_children()
        parser = ConfigParser(
            defaults=self.create_defaults,
            interpolation=ExtendedInterpolation())
        for c in children:
            for sec in c.sections:
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
        return parser
