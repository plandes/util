"""Peformance measure convenience utils.

"""
__author__ = 'Paul Landes'

from typing import Union
import logging
from logging import Logger
import inspect
import time as tm
import traceback as trc
from functools import wraps
from io import TextIOBase
import errno
import os
import signal

_time_logger = logging.getLogger(__name__)
TIMEOUT_DEFAULT = 10


class TimeoutError(Exception):
    """Raised when a time out even occurs in :func:`.timeout` or
    :class:`.timeprotect`.

    """
    pass


class time(object):
    """Used in a ``with`` scope that executes the body and logs the elapsed time.

    Format f-strings are supported as the locals are taken from the calling
    frame on exit.  This means you can do things like:

        with time('processed {cnt} items'):
            cnt = 5
            tm.sleep(1)

    which produeces: ``processed 5 items``.

    See the initializer documentation about special treatment for global
    loggers.

    """
    def __init__(self, msg: str = 'finished', level=logging.INFO,
                 logger: Union[Logger, TextIOBase] = None):
        """Create the time object.

        If a logger is not given, it is taken from the calling frame's global
        variable named ``logger``.  If this global doesn't exit it logs to
        standard out.  Otherwise, standard out/error can be used if given
        :obj:`sys.stdout` or :obj:`sys.stderr`.

        :param msg: the message log when exiting the closure

        :param logger: the logger to use for logging or a file like object
                       (i.e. :obj:`sys.stdout`) as a data sync

        :param level: the level at which the message is logged

        """
        self.msg = msg
        self.level = level
        if logger is None:
            frame = inspect.currentframe()
            try:
                globs = frame.f_back.f_globals
                if 'logger' in globs:
                    logger = globs['logger']
            except Exception as e:
                _time_logger.error(
                    f"Error in initializing time: {e} with '{msg}'",
                    exc_info=True)
                trc.print_exc()
        self.logger = logger

    @staticmethod
    def format_elapse(msg: str, seconds: int):
        mins = seconds / 60.
        hours = mins / 60.
        mins = int(mins % 60)
        hours = int(hours)
        sec_int = float(int(seconds % 60))
        sec_dec = seconds - int(seconds)
        lsd = sec_int + sec_dec
        tparts = []
        if hours > 0:
            suffix = 's' if hours > 1 else ''
            tparts.append(f'{hours} hour{suffix}')
        if mins > 0:
            suffix = 's' if mins > 1 else ''
            tparts.append(f'{mins} minute{suffix}')
            sfmt = '{:.0f}s'
        else:
            if sec_int > 0:
                sfmt = '{:.2f}s'
            else:
                lsd = int(lsd * 100)
                sfmt = '{:d}ms'
        tparts.append(sfmt.format(lsd))
        return f'{msg} in ' + ', '.join(tparts)

    def __enter__(self):
        self.t0 = tm.time()

    def __exit__(self, type, value, traceback):
        seconds = tm.time() - self.t0
        msg = self.msg
        frame = inspect.currentframe()
        try:
            locals = frame.f_back.f_locals
            msg = msg.format(**locals)
        except Exception as e:
            _time_logger.error(
                f"Error in exiting time: {e} with '{msg}'", exc_info=True)
        msg = self.format_elapse(msg, seconds)
        if self.logger is None:
            print(msg)
        elif isinstance(self.logger, Logger):
            self.logger.log(self.level, msg, stacklevel=2)
        else:
            self.logger.write(msg + '\n')


def timeout(seconds=TIMEOUT_DEFAULT, error_message=os.strerror(errno.ETIME)):
    """This creates a decorator called @timeout that can be applied to any long
    running functions.

    So, in your application code, you can use the decorator like so::

        from timeout import timeout

        # Timeout a long running function with the default expiry of
        # TIMEOUT_DEFAULT seconds.
        @timeout
        def long_running_function1():
            pass

    This was derived from the `David Narayan's <https://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish>`_
    StackOverflow thread.

    """
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


class timeprotect(object):
    """Invokes a block and bails if not completed in a specified number of seconds.

    :param seconds: the number of seconds to wait

    :param timeout_handler: function that takes a single argument, which is
                            this ``timeprotect`` object instance; if ``None``,
                            then nothing is done if the block times out

    :param context: an object accessible from the ``timeout_hander`` via
                          ``self``, which defaults to ``None``

    :see: :func:`timeout`

    """
    def __init__(self, seconds=TIMEOUT_DEFAULT, timeout_handler=None,
                 context=None, error_message=os.strerror(errno.ETIME)):
        self.seconds = seconds
        self.timeout_handler = timeout_handler
        self.context = context
        self.error_message = error_message
        self.timeout_handler_exception = None

    def __enter__(self):
        def _handle_timeout(signum, frame):
            signal.alarm(0)
            if self.timeout_handler is not None:
                try:
                    self.timeout_handler(self)
                except Exception as e:
                    _time_logger.exception(
                        f'could not recover from timeout handler: {e}')
                    self.timeout_handler_exception = e
            raise TimeoutError(self.error_message)

        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, cls, value, traceback):
        signal.alarm(0)
        return True
