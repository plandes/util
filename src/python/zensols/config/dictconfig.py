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
    def __init__(self, config: Dict[str, Dict[str, str]],
                 expect: bool = True, default_section: str = None):
        """Initialize.

        :param config: configures this instance (see class docs)

        :param expect: whether or not to raise an error when missing
                       options for all ``get_option*`` methods

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`

        """
        super().__init__(expect, default_section)
        if config is not None:
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
