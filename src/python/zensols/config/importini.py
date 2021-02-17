"""Contains a class for importing child configurations.

"""
__author__ = 'Paul Landes'

from typing import Iterable, Tuple, List
import logging
import sys
from io import StringIO
from collections import ChainMap
from configparser import ConfigParser, ExtendedInterpolation
from . import Configurable, IniConfig, ClassImporter

logger = logging.getLogger(__name__)


class _SharedExtendedInterpolation(ExtendedInterpolation):
    """Adds other :class:`Configurable` instances to available parameter to
    substitute.

    """
    def __init__(self, children: Tuple[Configurable]):
        super().__init__()
        self.children = children

    def before_get(self, parser: ConfigParser, section: str, option: str,
                   value: str, defaults: ChainMap):
        for c in self.children:
            if section in c.sections:
                defaults.new_child(c.get_options(section))
        return super().before_get(parser, section, option, value, defaults)


class _StringIniConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    :class:`~configparser.ExtendedInterpolation`.

    """
    def __init__(self, config: str, parent: IniConfig):
        super().__init__(
            parent.default_expect, parent.default_section, parent.default_vars)
        self.config = config
        self.children = []

    def _create_and_load_parser(self) -> ConfigParser:
        parser = ConfigParser(
            defaults=self.create_defaults,
            interpolation=_SharedExtendedInterpolation(self.children))
            #interpolation=ExtendedInterpolation())
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
    def __init__(self, *args, config_sec: str = 'config', **kwargs):
        if 'default_expect' not in kwargs:
            kwargs['default_expect'] = True
        super().__init__(*args, **kwargs)
        self.config_sec = config_sec

    def _mod_name(self) -> str:
        mname = sys.modules[__name__].__name__
        parts = mname.split('.')
        if len(parts) > 1:
            mname = '.'.join(parts[:-1])
        return mname

    def _get_bootstrap_parser(self):
        parser = IniConfig(self.config_file, default_expect=True)
        secs = set(parser.get_option_list('imports', self.config_sec))
        if parser.has_option('sections', self.config_sec):
            csecs = parser.get_option_list('sections', self.config_sec)
            secs.update(set(csecs))
        secs.add(self.config_sec)
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
        conf_sec = self.config_sec
        parser = self._get_bootstrap_parser()
        children: List[Configurable] = parser.children
        for sec in parser.get_option_list('imports', conf_sec):
            #print(f'populating section {sec}, {children}')
            params = parser.populate(section=sec).asdict()
            class_name = params.get('class_name')
            if class_name is None:
                tpe = params['type']
                del params['type']
                class_name = f'{mod_name}.{tpe.capitalize()}Config'
            else:
                del params['class_name']
            inst = ClassImporter(class_name, False).instance(**params)
            #print('ADDING', inst)
            children.append(inst)
        return children

    def _create_config_parser(self) -> ConfigParser:
        children = self._get_children()
        parser = ConfigParser(
            defaults=self.create_defaults,
            interpolation=_SharedExtendedInterpolation(children))
        for c in children:
            for sec in c.sections:
                parser.add_section(sec)
                for k, v in c.get_options(sec).items():
                    v = self._format_option(k, v, sec)
                    parser.set(sec, k, v)
        return parser
