"""Simplifies external process handling.

"""
__author__ = 'Paul Landes'

from typing import Tuple, Iterable, Union, Optional
from dataclasses import dataclass, field
import os
import logging
from logging import Logger
from pathlib import Path
import subprocess
from subprocess import Popen
from zensols.util import StreamLogDumper

logger = logging.getLogger(__name__)


@dataclass
class Executor(object):
    """Run a process and log output.  The process is run in the foreground by
    default, or background.  If the later, a process object is returned from
    :meth:`run`.

    """
    logger: Logger = field()
    """The client logger used to log output of the process."""

    dry_run: bool = field(default=False)
    """If ``True`` do not do anything, just log as if it were to act/do
    something.

    """
    check_exit_value: int = field(default=0)
    """Compare and raise an exception if the exit value of the process is not
    this number, or ``None`` to not check.

    """
    timeout: int = field(default=None)
    """The wait timeout in :meth:`wait`."""

    async_proc: bool = field(default=False)
    """If ``True``, return a process from :meth:`run`, which calls
    :meth:`wait`.

    """
    working_dir: Path = field(default=None)
    """Used as the `cwd` when creating :class:`.Popen`.

    """
    def __call__(self, cmd: Union[str, Iterable[str], Path]) -> \
            Optional[Union[Popen, int]]:
        """Run a command.

        :see: :meth:`.run`

        """
        return self.run(cmd)

    def run(self, cmd: Union[str, Iterable[str], Path]) -> \
            Optional[Union[Popen, int]]:
        """Run a commmand.

        :param cmd: either one string, a sequence of arguments or a path (see
                    :class:`subprocess.Popen`)

        :return: the process if :obj:`async_proc` is ``True``, otherwise,
                 the exit status of the subprocess

        """
        if logger.isEnabledFor(logging.INFO):
            if isinstance(cmd, (tuple, list)):
                cmd_str = ' '.join(cmd)
            else:
                cmd_str = str(cmd)
            logger.info(f'system <{cmd_str}>')
        if not self.dry_run:
            params = {'shell': isinstance(cmd, (str, Path)),
                      'stdout': subprocess.PIPE,
                      'stderr': subprocess.PIPE}
            if self.working_dir is not None:
                params['cwd'] = str(self.working_dir)
            proc = Popen(cmd, **params)
            StreamLogDumper.dump(proc.stdout, proc.stderr, self.logger)
            if self.async_proc:
                return proc
            else:
                return self.wait(proc)

    def wait(self, proc: Popen) -> int:
        """Wait for process ``proc`` to end and return the processes exit value.

        """
        ex_val = self.check_exit_value
        proc.wait(self.timeout)
        ret = proc.returncode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'exit value: {ret} =? {ex_val}')
        if ex_val is not None and ret != ex_val:
            raise OSError(f'command returned with {ret}, expecting {ex_val}')
        return ret


@dataclass
class ExecutableFinder(object):
    """Searches for an executable binary in the search path.  The default search
    path (:obj:`path_var`) is set to the operating system's ``PATH`` environment
    variable.

    """
    path_var: str = field(default=None)
    """The string that gives a delimited list of directories to search for an
    executable.  This defaults to the ``PATH`` variable separated by the path
    separator (i.e. ``:`` in UNIX/Linux).

    """
    raise_on_missing: bool = field(default=True)
    """Whether to raise errors when executables are not found."""

    def __post_init__(self):
        if self.path_var is None:
            self.path_var = os.environ.get('PATH', '')

    @property
    def search_path(self) -> Tuple[Path, ...]:
        """The search path dervied from :obj:`path_var`."""
        return tuple(map(Path, self.path_var.split(os.pathsep)))

    def find_all(self, name: str) -> Iterable[Path]:
        """Return matches of executable binary ``name``, if any."""
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'looking for executable: {name}')
        for path in self.search_path:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'searching directory: {path}')
            if not path.is_dir():
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f'not a directory: {path}--skipping')
            else:
                cand: Path = path / name
                if cand.is_file():
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(f'found matching executable: {path}')
                    yield cand

    def find(self, name: str) -> Path:
        """Like :meth:`find_all`, but returns only the first found executable.

        :raises OSError: if executable ``name`` is not found

        """
        execs: Tuple[Path, ...] = tuple(self.find_all(name))
        if len(execs) < 1:
            if self.raise_on_missing:
                raise OSError(f'Executable name found: {name}')
        return execs[0] if len(execs) > 0 else None
