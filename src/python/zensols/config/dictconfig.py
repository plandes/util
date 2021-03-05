"""Implementation of a dictionary backing configuration.

"""
__author__ = 'Paul Landes'

from typing import Dict, Set
from dataclasses import dataclass
import logging
from . import ConfigurableError, Configurable

logger = logging.getLogger(__name__)


@dataclass
class DictionaryConfig(Configurable):
    """This is a simple implementation of a dictionary backing configuration.  The
    provided configuration is just a two level dictionary.  The top level keys
    are the section and the values are a single depth dictionary with string
    keys and values.

    You can override :meth:`_get_config` to restructure the dictionary for
    application specific use cases.  One such example is
    :meth:`.JsonConfig._get_config`.

    .. document private functions
    .. automethod:: _get_config

    """
    def __init__(self, config: Dict[str, Dict[str, str]] = None,
                 default_section: str = None):
        """Initialize.

        :param config: configures this instance (see class docs)

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`

        """
        super().__init__(default_section)
        if config is None:
            self._dict_config = {}
        else:
            self._dict_config = config

    def _get_config(self) -> Dict[str, Dict[str, str]]:
        """Return the two level dict structure used for this configuration.

        """
        return self._dict_config

    def get_options(self, section: str = None) -> Dict[str, str]:
        conf = self._get_config()
        sec = conf.get(section)
        if sec is None:
            raise ConfigurableError(f'no section: {section}')
        return sec

    def has_option(self, name: str, section: str = None) -> bool:
        conf = self._get_config()
        sec = conf.get(section)
        if sec is not None:
            return sec.contains(name)
        return False

    @property
    def sections(self) -> Set[str]:
        """Return the top level keys of the dictionary as sections (see class doc).

        """
        return set(self._get_config().keys())

    def set_option(self, name: str, value: str, section: str = None):
        if section not in self.sections:
            dct = {}
            self._dict_config[section] = dct
        else:
            dct = self._dict_config[section]
        dct[name] = value
