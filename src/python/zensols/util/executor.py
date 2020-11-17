"""Simplifies external process handling.

"""
__author__ = 'Paul Landes'

from typing import Union
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
    :py:meth:`run`.

    :param logger: the client logger used to log output of the process

    :param dry_run: if ``True`` do not do anything, just log as if it were to
                    act/do something

    :param check_exit_value: compare and raise an exception if the exit value
                             of the process is not this number, or ``None`` to
                             not check

    :param timeout: the wait timeout in :meth:`wait`

    :param async_proc: if ``True``, return a process from :meth:`run`, which
                       calls :meth:`wait`

    """
    logger: Logger
    dry_run: bool = field(default=False)
    check_exit_value: int = field(default=0)
    timeout: int = field(default=None)
    async_proc: bool = field(default=False)
    working_dir: Path = field(default=None)

    def run(self, cmd) -> Union[Popen, int, type(None)]:
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'system <{cmd}>')
        if not self.dry_run:
            params = {'shell': True,
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
