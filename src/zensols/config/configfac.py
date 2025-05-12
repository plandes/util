"""Creates instances of :class:`.Configurable`.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Dict, Any, Type, Union, ClassVar
from dataclasses import dataclass, field
import sys
import logging
import inspect
from inspect import Signature
from pathlib import Path
from zensols.introspect import ClassImporter
from zensols.persist import persisted
from . import (
    ConfigurableError, Configurable, IniConfig, DictionaryConfig, Serializer
)

logger = logging.getLogger(__name__)


@dataclass
class _ConfigMeta(object):
    class_name: str = field()

    @property
    @persisted('_class_importer')
    def class_importer(self) -> ClassImporter:
        return ClassImporter(self.class_name, reload=False)

    @property
    @persisted('_signature')
    def signature(self) -> Signature:
        return inspect.signature(self.class_importer.get_class().__init__)

    @property
    def takes_parent(self) -> bool:
        return 'parent' in self.signature.parameters

    @property
    def takes_name(self) -> bool:
        return 'parent_section_name' in self.signature.parameters


@dataclass
class ConfigurableFactory(object):
    """Create instances of :class:`.Configurable` with factory methods.  The
    parameters in :obj:`kwargs` given to the initalizer on instantiation.

    This class often is used to create a factory from just a path, which then
    uses the extension with the :obj:`EXTENSION_TO_TYPE` mapping to select the
    class.  Top level/entry point configuration should use ``conf`` as the
    extension allowing the :class:`.ImportIni` to import other configuration.
    An example of this is the :class:`.ConfigurationImporter` loading user
    specific configuration.

    If the class uses ``type = import``, the type is prepended with ``import``
    and then mapped using :obj:`EXTENSION_TO_TYPE`.  This allows mixing of
    different files in one ``config_files`` entry and avoids multiple import
    sections.

    :see: `.ImportIniConfig`

    """
    _CONFIG_META: ClassVar[Dict[str, _ConfigMeta]] = {}

    EXTENSION_TO_TYPE: ClassVar[Dict[str, str]] = {
        'conf': 'ini',
        'ini': 'ini',
        'yml': 'yaml',
        'json': 'json'}
    """The configuration factory extension to clas name."""

    TYPE_TO_CLASS_PREFIX: ClassVar[Dict[str, str]] = {
        'import': 'ImportIni',
        'importini': 'ImportIni',
        'importyaml': 'ImportYaml',
        'importtree': 'ImportTree',
        'condyaml': 'ConditionalYaml'}
    """Mapping from :obj:`TYPE_NAME` option to class prefix."""

    TYPE_NAME: ClassVar[str] = 'type'
    """The section entry for the configurable type (eg ``ini`` vs ``yaml``)."""

    TYPE_MAP: ClassVar[str] = 'type_map'
    """The section entry for type map (see :obj:`type_map`)."""

    SINGLE_CONFIG_FILE: ClassVar[str] = 'config_file'
    """The section entry for the configuration file."""

    CLASS_NAME: ClassVar[str] = 'class_name'
    """The section entry for the class to use."""

    kwargs: Dict[str, Any] = field(default_factory=dict)
    """The keyword arguments given to the factory on creation."""

    type_map: Dict[str, str] = field(default_factory=dict)
    """Adds more mappings from extension to configuration factory types.

    :see: :obj:`EXTENSION_TO_TYPE`

    """
    parent: Configurable = field(default=None)
    """The client configuration using this instance to create a child."""

    parent_section_name: str = field(default=None)
    """The name of the section that has the definition creating a child."""

    def _mod_name(self) -> str:
        """Return the ``config`` (parent) module name."""
        mname = sys.modules[__name__].__name__
        parts = mname.split('.')
        if len(parts) > 1:
            mname = '.'.join(parts[:-1])
        return mname

    @property
    @persisted('_extension_to_type')
    def extension_to_type(self) -> Dict[str, str]:
        ext = dict(self.EXTENSION_TO_TYPE)
        ext.update(self.type_map)
        return ext

    def from_class_name(self, class_name: str) -> Configurable:
        """Create a configurable from the class name given.

        :param class_name: a fully qualified class name
                          (i.e. ``zensols.config.IniConfig``)

        :return: a new instance of a configurable identified by ``class_name``
                 and created with :obj:`kwargs`

        """
        config_meta: _ConfigMeta = self._CONFIG_META.get(class_name)
        if config_meta is None:
            config_meta = _ConfigMeta(class_name)
        params = dict(self.kwargs)
        if config_meta.takes_parent:
            params['parent'] = self.parent
        if config_meta.takes_name:
            params['parent_section_name'] = self.parent_section_name
        return config_meta.class_importer.instance(**params)

    def from_type(self, config_type: str) -> Configurable:
        """Create a configurable from the configuration type.

        :param config_type: one of the values in :obj:`EXTENSION_TO_TYPE`
                            (i.e. `importini`)

        :return: a new instance of a configurable identified by ``class_name``
                 and created with :obj:`kwargs`

        """
        mod_name: str = self._mod_name()
        extension_to_type = self.extension_to_type
        if config_type in extension_to_type:
            config_type = extension_to_type[config_type].capitalize()
        elif config_type in self.TYPE_TO_CLASS_PREFIX:
            config_type = self.TYPE_TO_CLASS_PREFIX[config_type]
        else:
            config_type = config_type.capitalize()
        class_name = f'{mod_name}.{config_type}Config'
        return self.from_class_name(class_name)

    def _path_to_type(self, path: Path) -> str:
        """Map a path to a ``config type``.  See :meth:`from_type`.

        """
        ext = path.suffix
        ext = None if len(ext) == 0 else ext[1:]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"using extension to map: '{ext}'")
        class_type = self.extension_to_type.get(ext)
        if class_type is None:
            class_type = 'importini'
        return class_type

    def from_path(self, path: Path) -> Configurable:
        """Create a configurable from a path.  This updates the :obj:`kwargs` to
        set ``config_file`` to the given path for the duration of this method.

        """
        if path.is_dir():
            inst = IniConfig(path, **self.kwargs)
        else:
            class_type = self._path_to_type(path)
            old_kwargs = self.kwargs
            self.kwargs = dict(self.kwargs)
            self.kwargs[self.SINGLE_CONFIG_FILE] = path
            try:
                inst = self.from_type(class_type)
            finally:
                self.kwargs = old_kwargs
        return inst

    def _get_path(self, config_file: Union[str, Path],
                  parent: Configurable) -> Path:
        config_path: Path = None
        if isinstance(config_file, str):
            sr = parent.serializer if parent is not None else Serializer()
            config_path = sr.parse_object(config_file)
            if not isinstance(config_path, Path):
                config_path = None
        if config_path is None:
            config_path = Path(config_file)
        return config_path

    @classmethod
    def from_section(cls: Type[ConfigurableFactory], kwargs: Dict[str, Any],
                     section: str, parent: Configurable = None) -> Configurable:
        params = dict(kwargs)
        class_name: str = params.get(cls.CLASS_NAME)
        type_map: Dict[str, str] = params.pop(cls.TYPE_MAP, {})
        self: ConfigurableFactory = cls(
            **{'type_map': type_map,
               'kwargs': params,
               'parent': parent,
               'parent_section_name': section})
        tpe: str = params.get(self.TYPE_NAME)
        config_file: Union[str, Dict[str, str], Path] = params.get(
            self.SINGLE_CONFIG_FILE)
        if isinstance(config_file, str):
            config_file = self._get_path(config_file, parent)
            params[self.SINGLE_CONFIG_FILE] = config_file
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'class: {class_name}, type: {tpe}, ' +
                         f'config: {config_file}, params: {params}')
        config: Configurable
        if class_name is not None:
            del params[self.CLASS_NAME]
            config = self.from_class_name(class_name)
        elif isinstance(config_file, dict):
            config = DictionaryConfig(config_file)
        elif tpe is not None:
            del params[self.TYPE_NAME]
            if tpe == 'import' and isinstance(config_file, Path):
                ext: str = config_file.suffix[1:]
                etype: str = self.extension_to_type.get(ext)
                if etype is not None:
                    tpe = f'import{etype}'
            config = self.from_type(tpe)
        elif config_file is not None:
            config = self.from_path(config_file)
        else:
            raise ConfigurableError(
                f"No loader information for '{section}': {params}")
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'created config: {config}')
        return config
