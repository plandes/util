"""Contains a class for importing child configurations.

"""
__author__ = 'Paul Landes'

from typing import Dict, Tuple, Iterable, Any
import logging
import sys
import inspect
from configparser import ConfigParser, ExtendedInterpolation
from . import Configurable, IniConfig, ClassImporter

logger = logging.getLogger(__name__)


class DelegateInterpolation(ExtendedInterpolation):
    def __init__(self, configurables: Tuple[Configurable]):
        if configurables is None:
            self.configurables = ()
        else:
            self.configurables = configurables

    def _get_children(self) -> Dict[str, str]:
        if not hasattr(self, '_children'):
            defs = {}
            for config in self.configurables:
                for sec in config.sections:
                    opts = config.get_options(sec)
                    for k, v in opts.items():
                        defs[f'{sec}:{k}'] = v
            self._children = defs
        return self._children

    def before_get(self, parser: ConfigParser, section: str, option: str,
                   value: str, defaults: Dict[str, str]):
        print(f'getting <{option}>, <{value}>')
        children = self._get_children()
        print(children)
        defaults = defaults.new_child(children)
        if parser.has_option(section, option):
            val = super().before_get(parser, section, option, value, defaults)
        if val is None:
            for par in self.configurables:
                val = parser.get_option(option, section, expect=False)
                if val is not None:
                    break
        return val


class ImportIniConfig(IniConfig):
    """A configuration that uses other :class:`.Configurable` classes to load other
    sections.  A special ``config`` section is given that indicates what other
    sections to load as children configuration.  Each of those indicated to
    import are processed in order by:

      1. Creating the delegate child :class:`Configurable` given in the section,

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

    def _instanceX(self, cname: str) -> Any:
        cs = tuple(
            map(lambda x: x[1],
                filter(lambda no: no[0] == cname and inspect.isclass(no[1]),
                       inspect.getmembers(sys.modules[__name__]))))
        if len(cs) != 1:
            raise ValueError(f'no class found: {cname}')
        return cs[0]

    def _mod_name(self) -> str:
        mname = sys.modules[__name__].__name__
        parts = mname.split('.')
        if len(parts) > 1:
            mname = '.'.join(parts[:-1])
        return mname

    def _get_children(self) -> Iterable[Configurable]:
        if not self.config_file.is_file():
            raise ValueError('not a file: {self.config_file}')
        mod_name = self._mod_name()
        conf_sec = self.config_sec
        parser = IniConfig(self.config_file, default_expect=True)
        children = []
        for sec in parser.get_option_list('imports', conf_sec):
            params = parser.populate(section=sec).asdict()
            class_name = params.get('class_name')
            if class_name is None:
                tpe = params['type']
                del params['type']
                class_name = f'{mod_name}.{tpe.capitalize()}Config'
            inst = ClassImporter(class_name, False).instance(**params)
            children.append(inst)
        return children

    def _create_config_parser(self) -> ConfigParser:
        children = self._get_children()
        parser = ConfigParser(
            defaults=self.create_defaults,
            interpolation=ExtendedInterpolation())
        for c in children:
            for sec in c.sections:
                parser.add_section(sec)
                for k, v in c.get_options(sec).items():
                    parser.set(sec, k, v)
        return parser
