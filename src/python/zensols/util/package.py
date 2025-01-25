"""A convenience class around the :mod:`pkg_resources` module.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Tuple, Sequence, Iterable, Optional, Type, Union, ClassVar
from dataclasses import dataclass, field
import logging
import re
from pathlib import Path
import pkg_resources as pkg
from .import APIError
from .writable import Writable, WritableContext

logger = logging.getLogger(__name__)


@dataclass
class PackageRequirement(Writable):
    """A Python requirement specification.

    """
    _COMMENT_REGEX: ClassVar[re.Pattern] = re.compile(r'^\s*#.*')
    _VER_REGEX: ClassVar[re.Pattern] = re.compile(r'^([^<>=]+)([<>=]+)(.+)$')
    _URL_REGEX: ClassVar[re.Pattern] = re.compile(r'^([^@]+) @ (.+)$')

    name: str = field()
    """The name of the module (i.e. zensols.someappname)."""

    version: str = field()
    """The version if the package exists."""

    version_constraint: str = field(default='==')
    """The constraint on the version as an (in)equality.  The following
    (limited) operators are ``==``, ``~=``, ``>`` etc.  However, multiple
    operators to specify intervals are not supported.

    """
    url: str = field(default=None)
    """The URL of the requirement."""

    def _write(self, c: WritableContext):
        c(self.name, 'name')
        c(self.version, 'version')

    @property
    def spec(self) -> str:
        """The specification such as ``plac==1.4.3``."""
        if self.url is not None:
            return f'{self.name} @ {self.url}'
        else:
            return self.name + self.version_constraint + self.version

    @classmethod
    def from_spec(cls: Type[PackageRequirement], spec: str) -> \
            Optional[PackageRequirement]:
        pr: PackageRequirement = None
        if cls._COMMENT_REGEX.match(spec) is None:
            ver: re.Match = cls._VER_REGEX.match(spec)
            if ver is not None:
                pr = PackageRequirement(
                    name=ver.group(1),
                    version_constraint=ver.group(2),
                    version=ver.group(3))
            else:
                url: re.Match = cls._URL_REGEX.match(spec)
                if url is not None:
                    pr = PackageRequirement(
                        name=url.group(1),
                        version=None,
                        url=url.group(2))
            if pr is None:
                raise APIError(f"Unknown requirement specification: '{spec}'")
        return pr

    def __repr__(self) -> str:
        return self.spec


@dataclass
class PackageResource(Writable):
    """Contains resources of installed Python packages.  It makes the
    :obj:`distribution` available and provides access to to resource files with
    :meth:`get_path` and as an index.

    """
    name: str = field()
    """The name of the module (i.e. zensols.someappname)."""

    @property
    def _distribution(self) -> Optional[pkg.DistInfoDistribution]:
        """The package distribution.

        :return: the distribution or ``None`` if it is not installed

        """
        if not hasattr(self, '_dist'):
            try:
                self._dist = pkg.get_distribution(self.name)
            except pkg.DistributionNotFound:
                logger.info(f'no distribution found: {self.name}')
                self._dist = None
        return self._dist

    @property
    def exists(self) -> bool:
        """Whether the package exists and installed."""
        return self._distribution is not None

    @property
    def version(self) -> Optional[str]:
        """The version if the package exists."""
        if self.exists:
            return self._distribution.version

    def get_package_requirement(self) -> Optional[PackageRequirement]:
        """The requirement represented by this instance."""
        if self.exists:
            return PackageRequirement(self.name, self.version)

    def get_path(self, resource: str) -> Optional[Path]:
        """Return a resource file name by name.  Optionally return resource as a
        relative path if the package does not exist.

        :param resource: a forward slash (``/``) delimited path
                        (i.e. ``resources/app.conf``) of the resource name

        :return: a path to that resource on the file system or ``None`` if the
                 package doesn't exist, the resource doesn't exist

        """
        res_name = str(Path(*resource.split('/')))
        path = None
        if self.exists and pkg.resource_exists(self.name, res_name):
            path = pkg.resource_filename(self.name, res_name)
            path = Path(path)
        else:
            path = Path(res_name)
        return path

    def _write(self, c: WritableContext):
        c(self.name, 'name')
        c(self.version, 'version')
        c(self.exists, 'exists')
        c(self._distribution, 'distribution')

    def __getitem__(self, resource: str) -> Path:
        if not self.exists:
            raise KeyError(f'package does not exist: {self.name}')
        res = self.get_path(resource)
        if res is None:
            raise KeyError(f'no such resource file: {resource}')
        return res

    def __str__(self) -> str:
        if self.exists:
            return str(self._distribution)
        else:
            return self.name
