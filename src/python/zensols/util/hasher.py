"""Utilities for hashing text.

"""
__author__ = 'Paul Landes'

from typing import Callable
from dataclasses import dataclass, field
import hashlib
import binascii
from . import APIError


@dataclass
class Hasher(object):
    short: bool = field(default=True)
    """Whether or not to generate a 32-bit or 64-bit key."""

    decode: str = field(default='hex')
    """The decoded output representation.  Choices are those ``b2a_*`` functions
    in :mod:`bin2ascii` such as ``hex``, ``base64``, etc.

    """
    def __post_init__(self):
        self.reset()

    def _create_algo(self):
        if self.short:
            self._algo = hashlib.blake2s()
        else:
            self._algo = hashlib.blake2b()
        self._ascii_fn = getattr(binascii, f'b2a_{self.decode}')

    def _assert_algo(self):
        if self._algo is None:
            self._create_algo()

    def reset(self):
        self._algo = None

    def update(self, text: str):
        """Update the hash from the text provided."""
        self._assert_algo()
        self._algo.update(text.encode())

    def __call__(self) -> str:
        """Create a hashed from ``text`` useful as file names representing the
        text provided.

        :param text: the text to hash

        """
        if self._algo is None:
            raise APIError('Must first call `update` to hash data')
        dig: bytes = self._algo.digest()
        fn: Callable = self._ascii_fn
        return fn(dig).decode().strip()
