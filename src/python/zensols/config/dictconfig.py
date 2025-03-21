"""Implementation of a dictionary backing configuration.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Dict, Set, Type, Any
import logging
from collections import OrderedDict
from . import ConfigurableError, Configurable, TreeConfigurable, Dictable

logger = logging.getLogger(__name__)


class DictionaryConfig(TreeConfigurable, Dictable):
    """This is a simple implementation of a dictionary backing configuration.
    The provided configuration is just a two level dictionary.  The top level
    keys are the section and the values are a single depth dictionary with
    string keys and values.

    You can override :meth:`_get_config` to restructure the dictionary for
    application specific use cases.  One such example is
    :meth:`.JsonConfig._get_config`.

    This configuration also allows Python source to be executed which allows
    sections and values to be created programatically.

    .. document private functions
    .. automethod:: _get_config

    """
    def __init__(self, config: Dict[str, Dict[str, Any]] = None,
                 default_section: str = None, deep: bool = False,
                 source: str = None, parent: Configurable = None):
        """Initialize.

        :param config: configures this instance (see class docs)

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`

        :param deep: whether or not to use the super class configuration methods

        :param source: source executed with :func:`exec` with variable
                       ``config`` available to programatically create sections
                       and values

        """
        super().__init__(default_section=default_section, parent=parent)
        config = {} if config is None else config
        self._dict_config = config
        self._deep = deep
        self._source = source
        self._initialized = False
        self.invalidate()

    @classmethod
    def from_config(cls: Type, source: Configurable,
                    **kwargs: Dict[str, Any]) -> DictionaryConfig:
        """Create an instance from another configurable.

        :param source: contains the source data from which to copy

        :param kwargs: initializer arguments for the new instance

        :return: a new instance of this class with the data copied from
                 ``source``

        """
        secs: Dict[str, Any] = OrderedDict()
        params: Dict[str, Any] = dict(kwargs)
        if 'default_section' not in params and \
           source.default_section is not None:
            params['default_section'] = source.default_section
        if isinstance(source, DictionaryConfig):
            params['deep'] = source.deep
        for sec in sorted(source.sections):
            svs = OrderedDict()
            secs[sec] = svs
            source.populate(svs, sec)
        return cls(secs, **kwargs)

    def _from_dictable(self, *args, **kwargs) -> Dict[str, Any]:
        return self._get_config()

    def _get_config(self) -> Dict[str, Any]:
        if self._source is not None:
            source: str = self._source
            self._source = None
            exec(source, {'config': self._dict_config, 'self': self})
        self._initialized = True
        return self._dict_config

    def _set_config(self, source: Dict[str, Any]):
        self._dict_config = source
        self._initialized = True
        self.invalidate()

    def _is_initialized(self) -> bool:
        return self._initialized

    @property
    def options(self) -> Dict[str, Any]:
        if self._deep:
            return super().options
        else:
            return Configurable.options.fget(self)

    def get_options(self, section: str = None) -> Dict[str, str]:
        if self._deep:
            return super().get_options(section)
        else:
            conf = self._get_config()
            sec = conf.get(section)
            if sec is None:
                raise ConfigurableError(f'no section: {section}')
            return sec

    def get_option(self, name: str, section: str = None) -> str:
        if self._deep:
            return super().get_option(name, section)
        else:
            return Configurable.get_option(self, name, section)

    def has_option(self, name: str, section: str = None) -> bool:
        if self._deep:
            return super().has_option(name, section)
        else:
            conf = self._get_config()
            sec = conf.get(section)
            if sec is not None:
                return name in sec
            return False

    @property
    def sections(self) -> Set[str]:
        """Return the top level keys of the dictionary as sections (see class
        doc).

        """
        if self._deep:
            return super().sections
        else:
            return set(self._get_config().keys())

    @sections.setter
    def sections(self, sections: Set[str]):
        raise RuntimeError('Can not set sections')

    def set_option(self, name: str, value: str, section: str = None):
        section = self.default_section if section is None else section
        if section not in self.sections:
            dct = {}
            self._dict_config[section] = dct
        else:
            dct = self._dict_config[section]
        dct[name] = value

    def remove_section(self, section: str):
        self._get_config().pop(section)

    def __repr__(self):
        return super().__repr__()
