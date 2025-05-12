"""Provides access to the system clipboard.  Currently only macOS is supported.

"""
__author__ = 'Paul Landes'

import logging
import subprocess
import platform
from . import APIError

logger = logging.getLogger(__name__)


class Clipboard(object):
    """A utility class that provides access to the system clipboard.

    """
    def _assert_available(self):
        plat: str = platform.system()
        if plat != 'Darwin':
            raise APIError(f'Clipboard is only supported on macOS: {plat}')

    def read(self) -> str:
        """Read text from the system clipboard and return it."""
        self._assert_available()
        text: str = subprocess.check_output(
            'pbpaste', env={'LANG': 'en_US.UTF-8'}).decode('utf-8')
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'read from clipboard: "{text}"')
        return text

    def write(self, text: str):
        """Copy ``text`` to the system clipboard."""
        self._assert_available()
        process = subprocess.Popen(
            'pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'copied to clipboard: "{text}"')
