"""Creates instances of :class:`.Configurable`.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any
from dataclasses import dataclass, field
import sys
import logging
import re
from pathlib import Path
from zensols.introspect import ClassImporter
from . import Configurable, IniConfig

logger = logging.getLogger(__name__)


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

    :see: `.ImportIniConfig`

    """
    EXTENSION_TO_TYPE = {'conf': 'ini',
                         'ini': 'ini',
                         'yml': 'yaml',
                         'json': 'json'}
    """The configuration factory extension to clas name.

    """

    FILE_EXT_REGEX = re.compile(r'.+\.([a-zA-Z]+?)$')
    """A regular expression to parse out the extension from a file name."""

    kwargs: Dict[str, Any] = field(default_factory=dict)
    """The keyword arguments given to the factory on creation."""

    def _mod_name(self) -> str:
        """Return the ``config`` (parent) module name."""
        mname = sys.modules[__name__].__name__
        parts = mname.split('.')
        if len(parts) > 1:
            mname = '.'.join(parts[:-1])
        return mname

    def from_class_name(self, class_name: str) -> Configurable:
        """Create a configurable from the class name given.

        :param class_name: a fully qualified class name
                          (i.e. ``zensols.config.IniConfig``)

        :return: a new instance of a configurable identified by ``class_name``
                 and created with :obj:`kwargs`

        """
        return ClassImporter(class_name, False).instance(**self.kwargs)

    def from_type(self, config_type: str) -> Configurable:
        """Create a configurable from the configuration type.

        :param config_type: one of the values in :obj:`EXTENSION_TO_TYPE`
                            (i.e. `importini`)

        :return: a new instance of a configurable identified by ``class_name``
                 and created with :obj:`kwargs`

        """
        mod_name: str = self._mod_name()
        if config_type == 'importini':
            config_type = 'ImportIni'
        else:
            config_type = config_type.capitalize()
        class_name = f'{mod_name}.{config_type}Config'
        return self.from_class_name(class_name)

    def _path_to_type(self, path: Path) -> str:
        """Map a path to a ``config type``.  See :meth:`from_type`.

        """
        m = self.FILE_EXT_REGEX.match(path.name)
        if m is not None:
            ext = m.group(1)
        else:
            ext = None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"using extension to map: '{ext}'")
        class_type = self.EXTENSION_TO_TYPE.get(ext)
        if class_type is None:
            class_type = 'importini'
        return class_type

    def from_path(self, path: Path) -> Configurable:
        """Create a configurable from a path.  This updates the :obj:`kwargs` to set
        ``config_file`` to the given path for the duration of this method.

        """
        if path.is_dir():
            inst = IniConfig(path, **self.kwargs)
        else:
            class_type = self._path_to_type(path)
            old_kwargs = self.kwargs
            self.kwargs = dict(self.kwargs)
            self.kwargs['config_file'] = path
            try:
                inst = self.from_type(class_type)
            finally:
                self.kwargs = old_kwargs
        return inst
