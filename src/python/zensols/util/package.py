"""A convenience class around the :mod:`pkg_resources` module.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Optional, Type, ClassVar
from dataclasses import dataclass, field
import importlib.metadata
import importlib.resources
import importlib.util
from importlib.machinery import ModuleSpec
import logging
import re
from pathlib import Path
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
    def _module_spec(self) -> Optional[ModuleSpec]:
        if not hasattr(self, '_module_spec_val'):
            self._module_spec_val = importlib.util.find_spec(self.name)
        return self._module_spec_val

    @property
    def version(self) -> Optional[str]:
        """The version if the package is installed."""
        if not hasattr(self, '_version'):
            self._version = None
            if self._module_spec is not None:
                try:
                    self._version = importlib.metadata.version(self.name)
                except importlib.metadata.PackageNotFoundError:
                    pass
        return self._version

    @property
    def installed(self) -> bool:
        """Whether the package is installed."""
        return self.version is not None

    @property
    def available(self) -> bool:
        """Whether the package exists but not installed."""
        return self._module_spec is not None

    def get_package_requirement(self) -> Optional[PackageRequirement]:
        """The requirement represented by this instance."""
        if self.available:
            return PackageRequirement(self.name, self.version)

    def get_path(self, resource: str) -> Optional[Path]:
        """Return a resource file name by name.  Optionally return resource as a
        relative path if the package does not exist.

        :param resource: a forward slash (``/``) delimited path
                        (i.e. ``resources/app.conf``) of the resource name

        :return: a path to that resource on the file system or ``None`` if the
                 package doesn't exist, the resource doesn't exist

        """
        path: Path = None
        rel_path: Path = Path(*resource.split('/'))
        if self.available:
            install_path: Path = importlib.resources.files(self.name)
            abs_path: Path = install_path / rel_path
            path = abs_path if abs_path.exists() else rel_path
        else:
            path = rel_path
        return path

    def _write(self, c: WritableContext):
        c(self.name, 'name')
        c(self.version, 'version')
        c(self.available, 'available')
        c(self.installed, 'installed')

    def __getitem__(self, resource: str) -> Path:
        if not self.available:
            raise KeyError(f'Package does not exist: {self.name}')
        res = self.get_path(resource)
        if res is None:
            raise KeyError(f'No such resource file: {resource}')
        return res

    def __repr__(self) -> str:
        if self.available:
            return f'{self.name}=={self.version}'
        else:
            return self.name
