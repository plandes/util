"""Like :class:`.YamlConfig` but supports configuration importation like
:class:`.ImportIniConfig`.

"""
__author__ = 'Paul Landes'

from typing import Dict, Union, Any
from pathlib import Path
import logging
from string import Template
from io import TextIOBase
from . import Serializer, ConfigurableFactory, YamlConfig

logger = logging.getLogger(__name__)


class _Template(Template):
    idpattern = r'[a-z0-9_:]+'


class ImportYamlConfig(YamlConfig):
    def __init__(self, config_file: Union[Path, TextIOBase] = None,
                 default_section: str = None, sections_name: str = 'sections',
                 import_name: str = 'import'):
        super().__init__(config_file, default_section, default_vars=None,
                         delimiter=None, sections_name=sections_name)
        self.import_name = import_name
        self.serializer = Serializer()

    def _post_config(self):
        def repl_node(par: Dict[str, Any]):
            repl = {}
            for k, c in par.items():
                if isinstance(c, dict):
                    repl_node(c)
                elif isinstance(c, str):
                    template = _Template(c)
                    rc = template.safe_substitute(context)
                    repl[k] = rc
            par.update(repl)

        import_def: Dict[str, Any] = self.get_options(
            f'{self.root}.{self.import_name}')
        cnf: Dict[str, Any] = {}
        context: Dict[str, str] = {}

        if import_def is not None:
            for sec_name, params in import_def.items():
                config = ConfigurableFactory.from_section(params, sec_name)
                for sec in config.sections:
                    cnf[sec] = config.get_options(section=sec)

        self._config.update(cnf)
        self._flatten(context, '', self._config, ':')
        new_keys = set(map(lambda k: k.replace(':', '.'), context.keys()))
        self._all_keys.update(new_keys)
        repl_node(self._config)

    def _compile(self) -> Dict[str, Any]:
        def serialize(par: Dict[str, Any]):
            repl = {}
            for k, c in par.items():
                if isinstance(c, dict):
                    serialize(c)
                elif isinstance(c, str):
                    repl[k] = self.serializer.parse_object(c)
            par.update(repl)

        root: Dict[str, Any] = super()._compile()
        self._config = root
        self._post_config()
        serialize(root)
        return root
