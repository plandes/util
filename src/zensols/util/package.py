"""A convenience class around the :mod:`pkg_resources` module.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Dict, List, Tuple, Iterable, Union, Optional, Type, ClassVar
from dataclasses import dataclass, field
import sys
import subprocess
from itertools import chain
import importlib.metadata
import importlib.resources
import importlib.util
from importlib.machinery import ModuleSpec
import logging
import re
from pathlib import Path
from .writable import Writable, WritableContext
from .import APIError

logger = logging.getLogger(__name__)


class PackageError(APIError):
    """Raised for errors related to packages from this module."""
    pass


@dataclass(order=True, frozen=True)
class PackageRequirement(Writable):
    """A Python requirement specification.

    """
    _COMMENT_REGEX: ClassVar[re.Pattern] = re.compile(r'^\s*#.*')
    _URL_REGEX: ClassVar[re.Pattern] = re.compile(r'^([^@]+) @ (.+)$')
    _VER_REGEX: ClassVar[re.Pattern] = re.compile(
        r'^(^[a-z0-9]+(?:[_-][a-z0-9]+)*)([<>~=]+)(.+)$')
    _NON_VER_REGEX: ClassVar[re.Pattern] = re.compile(
        r'^(^[a-z0-9]+(?:[_-][a-z0-9]+)*)$')

    name: str = field()
    """The name of the module (i.e. zensols.someappname)."""

    version: str = field(default=None)
    """The version if the package exists."""

    version_constraint: str = field(default='==')
    """The constraint on the version as an (in)equality.  The following
    (limited) operators are ``==``, ``~=``, ``>`` etc.  However, multiple
    operators to specify intervals are not supported.

    """
    url: str = field(default=None)
    """The URL of the requirement."""

    source: Path = field(default=None)
    """The file in which the requirement was parsed."""

    meta: Dict[str, str] = field(default=None)

    @property
    def spec(self) -> str:
        """The specification such as ``plac==1.4.3``."""
        spec: str
        if self.url is not None:
            spec = f'{self.name} @ {self.url}'
        else:
            spec: str
            if self.version is None:
                spec = self.name
            else:
                spec = self.name + self.version_constraint + self.version
        return spec

    @classmethod
    def from_spec(cls: Type[PackageRequirement], spec: str, **kwargs) -> \
            Optional[PackageRequirement]:
        pr: PackageRequirement = None
        if cls._COMMENT_REGEX.match(spec) is None:
            if pr is None:
                m: re.Match = cls._URL_REGEX.match(spec)
                if m is not None:
                    pr = PackageRequirement(
                        name=m.group(1),
                        version=None,
                        version_constraint=None,
                        url=m.group(2),
                        **kwargs)
            if pr is None:
                m: re.Match = cls._VER_REGEX.match(spec)
                if m is not None:
                    pr = PackageRequirement(
                        name=m.group(1),
                        version_constraint=m.group(2),
                        version=m.group(3),
                        **kwargs)
            if pr is None:
                m: re.Match = cls._NON_VER_REGEX.match(spec)
                if m is not None:
                    pr = PackageRequirement(m.group(1), **kwargs)
            if pr is None:
                raise APIError(f"Unknown requirement specification: '{spec}'")
        return pr

    def _write(self, c: WritableContext):
        c(self.name, 'name')
        c(self.version, 'version')
        c(self.url, 'url')
        c(self.source, 'source')
        c(self.meta, 'meta')

    def __repr__(self) -> str:
        return self.spec


@dataclass
class PackageResource(Writable):
    """Contains resources of installed Python packages.  It makes the
    :obj:`distribution` available and provides access to to resource files with
    :meth:`get_path` and as an index.

    """
    name: str = field()
    """The name of the module (i.e. ``zensols.someappname``)."""

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

    def to_package_requirement(self) -> Optional[PackageRequirement]:
        """The requirement represented by this instance."""
        from importlib.metadata import PackageMetadata
        if self.available:
            try:
                pm: PackageMetadata = importlib.metadata.metadata(self.name)
                meta: Dict[str, str] = {k.lower(): v for k, v in pm.items()}
                return PackageRequirement(
                    name=meta.pop('name'),
                    version=meta.pop('version'),
                    meta=meta)
            except importlib.metadata.PackageNotFoundError:
                pass

    def get_path(self, resource: str) -> Optional[Path]:
        """Return a resource file name by name.  Optionally return resource as a
        relative path if the package does not exist.

        :param resource: a forward slash (``/``) delimited path
                        (i.e. ``resources/app.conf``) of the resource name

        :return: a path to that resource on the file system or ``None`` if the
                 package doesn't exist, the resource doesn't exist

        """
        path: Path = None
        rel_path: Path = Path(resource)
        if not rel_path.is_file():
            rel_path = Path(*resource.split('/'))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'relative path: {resource} -> {rel_path}')
        if self.available:
            try:
                install_path: Path = importlib.resources.files(self.name)
                abs_path: Path = install_path / rel_path
                path = abs_path if abs_path.exists() else rel_path
            except TypeError:
                path = rel_path
        else:
            path = rel_path
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'package path: {path}')
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


@dataclass
class PackageManager(object):
    """Gather and parse requirements and optionally install them.

    """
    _FIELD_REGEX: ClassVar[re.Pattern] = re.compile(
        r'^([A-Z][a-z-]+):(?: (.+))?$')

    pip_install_args: Tuple[str, ...] = field(
        default=('--use-deprecated=legacy-resolver',))
    """Additional argument used for installing packages with ``pip``."""

    def _get_requirements_from_file(self, source: Path) -> \
            Iterable[PackageRequirement]:
        try:
            with open(source) as f:
                spec: str
                for spec in map(str.strip, f.readlines()):
                    req: PackageRequirement = PackageRequirement.from_spec(
                        spec=spec,
                        source=source)
                    if req is not None:
                        yield req
        except Exception as e:
            raise PackageError(
                f"Can not parse requirements from '{source}': {e}") from e

    def _get_requirements(self, source: Union[str, Path, PackageRequirement]) \
            -> Iterable[PackageRequirement]:
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"resolving requirements from '{source}'")
        if isinstance(source, PackageRequirement):
            yield source
        elif isinstance(source, str):
            req: PackageRequirement = PackageRequirement.from_spec(source)
            if req is not None:
                yield req
        elif isinstance(source, Path):
            if source.is_file():
                req: PackageRequirement
                for req in self._get_requirements_from_file(source):
                    yield req
            elif source.is_dir():
                path: Path
                for path in source.iterdir():
                    req: PackageRequirement
                    for req in self._get_requirements_from_file(path):
                        yield req
            else:
                raise PackageError(f'Not a file or directory: {path}')
        else:
            raise PackageError('Expecting a string, path or requirement ' +
                               f'but got: {type(source)}')

    def find_requirements(self, sources:
                          Tuple[Union[str, Path, PackageRequirement], ...]) -> \
            Tuple[PackageRequirement, ...]:
        """The requirements contained in this manager.  .

        :param sources: the :obj:PackageRequirement.spec`, requirements file, or
                        directory with requirements files

        """
        return tuple(sorted(chain.from_iterable(
            map(self._get_requirements, sources))))

    def _invoke_pip(self, args: List[str],
                    raise_exception: bool = True) -> str:
        cmd: List[str] = [sys.executable, "-m", "pip"] + args
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'pip command: {cmd}')
        res: subprocess.CompletedProcess = subprocess.run(
            cmd, capture_output=True, text=True)
        if raise_exception and res.returncode != 0:
            raise PackageError(f'Unable to run pip: {res.stderr}')
        output: str = res.stdout.strip()
        return output

    def get_installed_requirement(self, package: str) -> \
            Optional[PackageRequirement]:
        """Get an already installed requirement by name.

        :param package: the package name (i.e. ``zensols.util``)

        """
        output: str = self._invoke_pip(['show', package], raise_exception=False)
        meta: Dict[str, str] = {}
        if len(output) > 0:
            line: str
            for line in map(str.strip, output.split('\n')):
                m: re.Match = self._FIELD_REGEX.match(line)
                if m is None:
                    raise PackageError(f"Bad pip show format: <{line}>")
                meta[m.group(1).lower()] = m.group(2)
            return PackageRequirement(
                name=meta.pop('name'),
                version=meta.pop('version'),
                meta=meta)

    def get_requirement(self, package: str) -> Optional[PackageRequirement]:
        """First try to get an installed (:meth:`get_installed_requirement), and
        if not found, back off to finding one with :class:`.PackageResource`.

        :param package: the package name (i.e. ``zensols.util``)

        """
        req: PackageRequirement = self.get_installed_requirement(package)
        if req is None:
            pr = PackageResource(package)
            req = pr.to_package_requirement()
        return req

    def install(self, requirement: PackageRequirement, no_deps: bool = False):
        """Install a package in this Python enviornment with pip.

        :param requirement: the requirement to install

        :param no_deps: if ``True`` do not install the package's dependencies

        :return: the output from the pip command invocation

        """
        args: List[str] = ['install']
        args.extend(self.pip_install_args)
        if no_deps:
            args.append('--no-deps')
        args.append(requirement.spec)
        output: str = self._invoke_pip(args)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'pip: {output}')
        return output

    def uninstall(self, requirement: PackageRequirement) -> str:
        """Uninstall a package in this Python enviornment with pip.

        :param requirement: the requirement to uninstall

        :param no_deps: if ``True`` do not install the package's dependencies

        :return: the output from the pip command invocation

        """
        args: List[str] = ['uninstall', '-y']
        args.extend(self.pip_install_args)
        args.append(requirement.spec)
        output: str = self._invoke_pip(args)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'pip: {output}')
        return output
