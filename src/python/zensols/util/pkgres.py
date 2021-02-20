"""A convenience class around the :mod:`pkg_resources` module.

"""
__author__ = 'Paul Landes'

from typing import Optional
from dataclasses import dataclass, field
import logging
from pathlib import Path
import pkg_resources as pkg

logger = logging.getLogger(__name__)


@dataclass
class PackageResource(object):
    """Contains resources of installed Python packages.  It makes the
    :obj:`distribution` available and provides access to to resource files with
    :meth:`get_path` and as an index.

    """
    name: str = field()
    """The name of the module (i.e. zensols.someappname)."""

    file_system_defer: bool = field(default=True)
    """Whether or not to return resource paths that point to the file system when
    this package distribution does not exist.

    :see: :meth:`get_path`

    """

    @property
    def distribution(self) -> Optional[pkg.DistInfoDistribution]:
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
        """Return if the package exists and installed.

        """
        return self.distribution is not None

    @property
    def version(self) -> Optional[str]:
        """Return the version if the package exists.

        """
        if self.exists:
            return self.distribution.version

    def get_path(self, resource: str) -> Optional[Path]:
        """Return a resource file name by name.  Optionally return resource as a
        relative path if the package does not exist.

        :param resource: a forward slash (``/``) delimited path
                        (i.e. ``resources/app.conf``) of the resource name

        :return: a path to that resource on the file system or ``None`` if the
                 package doesn't exist, the resource doesn't exist and
                 :obj:`file_system_defer` is ``False``

        """
        res_name = str(Path(*resource.split('/')))
        path = None
        if self.exists and pkg.resource_exists(self.name, res_name):
            path = pkg.resource_filename(self.name, res_name)
            path = Path(path)
        else:
            path = Path(res_name)
        return path

    def __getitem__(self, resource: str) -> Path:
        if not self.exists:
            raise KeyError(f'package does not exist: {self.name}')
        res = self.get_path(resource)
        if res is None:
            raise KeyError(f'no such resource file: {resource}')
        return res

    def __str__(self) -> str:
        if self.exists:
            return str(self.distribution)
        else:
            return self.name
