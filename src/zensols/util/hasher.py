"""Utilities for hashing text.

"""
__author__ = 'Paul Landes'
from typing import Tuple, Dict, Iterable, Any, Callable, Union, Protocol
from dataclasses import dataclass, field
from pathlib import Path
import base64
import hashlib
import binascii
from . import APIError


class HashAlgorithm(Protocol):
    """A type for :mod:`hashlib` hashers (see :obj:`Hasher.decode`).

    """
    def update(self, data: bytes) -> None:
        ...

    def digest(self) -> bytes:
        ...


@dataclass
class Hasher(object):
    """A utility class that creates hash values for text.  By default,
    :func:`hashlib.blake2s` with a size of 20 (:obj:`short`) is used to create
    teh digest, which is then encoded with
    :func:`~base64.b2a_urlsafe_b64encode`.  Finally, the string is encoded using
    ``str.encode('ascii')``.  This default creates output strings that are 40
    characters long.  Setting :obj:`short` to 16 also produces strongly unique
    strings of length 22.

    :see: :mod:`hashlib`

    """
    short: Union[bool, int] = field(default=20)
    """Whether to generate a short 20-bit or long 64-bit key.  When set to an
    integer, It is interpreted as the digest size.  For hexidecimal the string
    length is twice that of the digest size.  See the class docs for the default
    output string lengths.

    """
    decode: str = field(default='url')
    """The decoded output representation.  Choices are those ``b2a_*`` functions
    in :mod:`binascii` such as :func:`~binascii.b2a_hex`,
    :func:`~binascii.b2a_base64`, etc.  The default (``url``) is safe for URLs
    and file name, which uses :func:`~base64.b2a_urlsafe_b64encode`.

    """
    def __post_init__(self):
        if isinstance(self.short, bool):
            # bool = you’re explicitly choosing algo
            if self.short:
                # blake2s default digest size
                self._size = 20
            else:
                # blake2b default digest size
                self._size = 64
        else:
            # int = digest size in bytes; pick algo accordingly
            size = int(self.short)
            if size <= 0:
                raise APIError('Digest size must be positive')
            if size <= 32:
                # blake2s supports 1–32 bytes
                self.short = True  # _create_algo picks blake2s
                self._size = size
            else:
                # blake2b supports 1–64 bytes
                if size > 64:
                    raise APIError('Digest size for blake2b must be <= 64')
                self.short = False  # _create_algo picks blake2b
                self._size = size
        self.reset()

    def reset(self):
        self._algo: HashAlgorithm = None
        self._ascii_fn: Callable = None

    def _create_algo(self) -> Tuple[HashAlgorithm, Callable]:
        def url_safe(b: bytes) -> bytes:
            # not reverse decodable, which isn't needed
            return base64.urlsafe_b64encode(b).rstrip(b'=')

        algo: HashAlgorithm
        ascii_fn: Callable
        if self.short:
            algo = hashlib.blake2s(digest_size=self._size)
        else:
            algo = hashlib.blake2b(digest_size=self._size)
        if self.decode == 'url':
            ascii_fn = url_safe
        else:
            ascii_fn = getattr(binascii, f'b2a_{self.decode}')
        return algo, ascii_fn

    def _assert_algo(self):
        if self._algo is None:
            self._algo, self._ascii_fn = self._create_algo()

    def _update(self, data: Any) -> str:
        algo = self._algo
        if isinstance(data, str):
            algo.update(data.encode())
        elif isinstance(data, (bool, float, int, Path)):
            algo.update(str(data).encode())
        elif isinstance(data, Dict):
            for k, v in sorted(data.items(), key=lambda t: t[0]):
                self._update(k)
                self._update(v)
        elif isinstance(data, Iterable):
            for o in data:
                self._update(o)
        else:
            raise APIError(f'No support for hashing type {type(data)}')

    def update(self, data: Any):
        """Update the hash from the data provided.  The data is converted to a
        string, and then used to update the hash.  The allowed types for
        ``data`` are:

          * :class:`str`
          * :class:`float`
          * :class:`int`
          * :class:`bool`
          * :class:`~pathlib.Path`
          * :class:`~typing.Dict` with keys and values of types in this list
          * :class:`~typing.Iterable` with other data with types in this list

        :param data: the data used to update the hash value encapsulted in this
                     object instance

        """
        self._assert_algo()
        self._update(data)

    def __call__(self, output_bytes: bool = False) -> Union[str, bytes]:
        """Create a hashed from ``text`` useful as file names representing the
        text provided.

        :param output_bytes: whether to return the hashed text as a byte array
                             or string

        :return: either encoded digest as a byte array or a string depending on
                 ``output_bytes``

        """
        if self._algo is None:
            raise APIError('Must first call `update` to hash data')
        fn: Callable = self._ascii_fn
        digest: bytes = self._algo.digest()
        hash_val: bytes = fn(digest)
        if output_bytes:
            return digest
        else:
            return hash_val.decode('ascii').rstrip()
