"""Simplifies external process handling.

"""
__author__ = 'Paul Landes'

from typing import Union, Iterable
from dataclasses import dataclass, field
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

    def run(self, cmd: Union[str, Iterable[str], Path]) -> \
            Union[Popen, int, type(None)]:
        """Run a commmand.

        :param cmd: either one string, a sequence of arguments or a path (see
                    :class:`subprocess.Popen`)

        :return: the process if :obj:`async_proc` is ``True``, otherwise,
                 return return value

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
        ex_val = self.check_exit_value
        proc.wait(self.timeout)
        ret = proc.returncode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'exit value: {ret} =? {ex_val}')
        if ex_val is not None and ret != ex_val:
            raise OSError(f'command returned with {ret}, expecting {ex_val}')
        return ret
