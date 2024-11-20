"""Extends the import capability of YAML files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Sequence, List, Union, ClassVar
import logging
import random
import string
from . import Configurable, DictionaryConfig, ImportIniConfig

logger = logging.getLogger(__name__)


class ImportTreeConfig(DictionaryConfig):
    """A :class:`.Configurable` that give :class:`.ImortIniConfig` capabilities
    to any gree based configuration, and specifically
    :class:`.ImportYamlConfig`.
    """
    DEFAULT_TYPE_MAP: ClassVar[Dict[str, str]] = {
        'yml': 'condyaml', 'conf': 'importini'}

    def __init__(self, parent_section_name: str, parent: Configurable,
                 **kwargs):
        self._parent_section_name = parent_section_name
        self._import_section = None
        super().__init__(default_section=None, parent=parent)
        self._import_section: Dict[str, Any] = kwargs
        # print('name:', parent_section_name)
        # print('parent:', parent)
        # print('kwargs:', kwargs)

    def _get_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = super()._get_config()
        if self._import_section is not None:
            self._import_tree(self._import_section, config)
            self._import_section = None
        return config

    def _create_sec_name(self) -> str:
        sec_name: str = self._parent_section_name
        if sec_name is None or len(sec_name) == 0:
            sec_name = ''
        rand = ''.join(random.choices(string.ascii_lowercase, k=10))
        return f'{sec_name}_{rand}'

    def _import_tree(self, source: Dict[str, Any], target: Dict[str, Any]):
        def map_cf(obj) -> str:
            if isinstance(obj, Dict) and len(obj) == 1:
                t = next(iter(obj.items()))
                return f'{t[0]}: {t[1]}'
            return obj

        sec: Dict[str, Any] = source
        sec_name: str = self._create_sec_name()
        cleanups: List[str] = sec.pop(ImportIniConfig.CLEANUPS_NAME, [])
        type_map: str = sec.pop(ImportIniConfig.TYPE_MAP, self.DEFAULT_TYPE_MAP)
        files: Union[str, Sequence[Any]] = sec[ImportIniConfig.CONFIG_FILES]
        if isinstance(files, str):
            files = tuple(filter(lambda s: len(s) > 0, files.split('\n')))
        files = tuple(map(map_cf, files))
        sec[ImportIniConfig.CONFIG_FILES] = self.serializer.format_option(files)
        if self._parent_section_name is not None:
            cleanups.append(self._parent_section_name)
        sec.pop(ImportIniConfig.TYPE_NAME, None)
        imp_sec: Dict[str, Any] = {
            ImportIniConfig.SECTIONS_SECTION:
            self.serializer.format_option([sec_name]),
        }
        op: str
        for op in (ImportIniConfig.REFS_NAME, ImportIniConfig.CLEANUPS_NAME):
            val: Any = sec.pop(op, None)
            if val is not None:
                imp_sec[op] = self.serializer.format_option(val)
        sec[ImportIniConfig.TYPE_MAP] = self.serializer.format_option(type_map)
        dc = DictionaryConfig({
            ImportIniConfig.IMPORT_SECTION: imp_sec,
            sec_name: sec})
        iniconfig = ImportIniConfig(
            dc,
            children=self.parent.children,
            parent=self.parent)
        dc = DictionaryConfig(target)
        iniconfig.copy_sections(dc)
        if len(cleanups) > 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'removing {cleanups}')
            parent: Configurable = self.parent
            while parent is not None:
                if isinstance(parent, ImportIniConfig):
                    parent.remove_sections.extend(cleanups)
                parent = parent.parent
