"""Extends the import capability of YAML files.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Sequence, List, Set, Union, ClassVar
import logging
import random
import string
from . import (
    ConfigurableError, Serializer,
    Configurable, DictionaryConfig, ImportIniConfig
)

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

    def _get_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = super()._get_config()
        if self._import_section is not None:
            self._import_tree(self._import_section, config)
            self._import_section = None
        return config

    def _create_sec_name(self) -> str:
        """Return a unique section name based off this (parent) section name."""
        sec_name: str = self._parent_section_name
        if sec_name is None or len(sec_name) == 0:
            sec_name = ''
        rand = ''.join(random.choices(string.ascii_lowercase, k=10))
        return f'{sec_name}_{rand}'

    def _create_import_config(self, sec: Dict[str, Any]) -> Dict[str, Any]:
        """Return a dict with the :class:`.Configurable` import sections and a
        list of cleanups.

        """
        def map_cf(obj) -> str:
            if isinstance(obj, Dict) and len(obj) == 1:
                t = next(iter(obj.items()))
                return f'{t[0]}: {t[1]}'
            return obj

        ser: Serializer = self.serializer
        # create a unique import section name
        sec_name: str = self._create_sec_name()
        # sections to remove after
        cleanups: List[str] = sec.pop(ImportIniConfig.CLEANUPS_NAME, [])
        # the extension to Configurable class
        type_map: str = sec.pop(ImportIniConfig.TYPE_MAP, self.DEFAULT_TYPE_MAP)
        # get the config files to load (plural and singular nomenclatures)
        files: Union[str, Sequence[Any]] = sec.get(
            ImportIniConfig.CONFIG_FILES, [])
        sfile: str = sec.pop(ImportIniConfig.SINGLE_CONFIG_FILE, None)
        # find entries that don't belong
        unknown_entries: Set[str] = \
            (set(sec.keys()) - ImportIniConfig.IMPORT_SECTION_FIELDS)
        if len(unknown_entries) > 0:
            raise ConfigurableError(
                f'Unknown configuration entries: {unknown_entries}')
        # adding files/resources to load can be as a string, list, or what the
        # YAML parser creates as a list of dicts for ``resource:...``; validate
        if isinstance(files, str):
            files = tuple(filter(lambda s: len(s) > 0, files.split('\n')))
        if sfile is not None:
            files.append(ser.format_option(sfile))
        files = tuple(map(map_cf, files))
        if len(files) == 0:
            raise ConfigurableError(f'No configuration files set: {self}')
        # add the processed files to the inmport section
        sec[ImportIniConfig.CONFIG_FILES] = ser.format_option(files)
        # and the current section (yaml based) import section
        if self._parent_section_name is not None:
            cleanups.append(self._parent_section_name)
        # remove ``type: treeimport`` from the section
        sec.pop(ImportIniConfig.TYPE_NAME, None)
        # create the import section
        imp_sec: Dict[str, Any] = {
            ImportIniConfig.SECTIONS_SECTION:
            ser.format_option([sec_name])}
        # use the serializer to convert Python objects and types to strings
        op: str
        for op in (ImportIniConfig.REFS_NAME, ImportIniConfig.CLEANUPS_NAME):
            val: Any = sec.pop(op, None)
            if val is not None:
                imp_sec[op] = ser.format_option(val)
        # same for the top level ``import`` section
        for op in (ImportIniConfig.ENABLED_NAME,):
            val: Any = sec.pop(op, None)
            if val is not None:
                sec[op] = ser.format_option(val)
        sec[ImportIniConfig.TYPE_MAP] = ser.format_option(type_map)
        # create the config with the top level ``import`` and import section
        config = DictionaryConfig({ImportIniConfig.IMPORT_SECTION: imp_sec,
                                   sec_name: sec})
        return {'config': config,
                'cleanups': cleanups}

    def _import_tree(self, source: Dict[str, Any], target: Dict[str, Any]):
        """Create a new :class:`.ImportIniConfig` with import sections to load
        configuration for the section build for this instance.

        :param source: the section in the YAML that tells us what to import

        :param target: the data to populate with the imported data

        """
        # create the input to ImportIniConfig
        import_data: Dict[str, Any] = self._create_import_config(source)
        cleanups: List[str] = import_data['cleanups']
        # create the import configurable instance with importini context
        iniconfig = ImportIniConfig(
            import_data['config'],
            children=self.parent.children,
            parent=self.parent)
        # preemptively remove sections so they deep dicts don't interfere with
        # the copying of sections
        if len(cleanups) > 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'removing {cleanups}')
            parent: Configurable = self.parent
            while parent is not None:
                if parent._is_initialized():
                    for sec in cleanups:
                        parent.remove_section(sec)
                parent = parent.parent
        # copy the imported sections to our config
        dc = DictionaryConfig(target)
        iniconfig.copy_sections(dc)
