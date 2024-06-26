"""Utility classes and context managers around logging.

"""
__author__ = 'Paul Landes'

from typing import List, Union
import logging
from logging import Logger
import sys
import threading
from io import StringIO


class LoggerStream(object):
    """Each line of standard out/error becomes a logged line

    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, c):
        if c == '\n':
            self.logger.log(self.log_level, self.linebuf.rstrip())
            self.linebuf = ''
        else:
            self.linebuf += c

    def flush(self):
        if len(self.linebuf) > 0:
            self.write('\n')


class LogLevelSetFilter(object):
    def __init__(self, levels):
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


class StreamLogDumper(threading.Thread):
    """Redirect stream output to a logger in a running thread.

    """
    def __init__(self, stream, logger, level):
        super().__init__()
        self.stream = stream
        self.logger = logger
        self.level = level

    def run(self):
        with self.stream as s:
            for line in iter(s.readline, b''):
                line = line.decode('utf-8')
                line = line.rstrip()
                self.logger.log(self.level, line)

    @staticmethod
    def dump(stdout, stderr, logger: Logger):
        StreamLogDumper(stdout, logger, logging.INFO).start()
        StreamLogDumper(stderr, logger, logging.ERROR).start()


class LogConfigurer(object):
    """Configure logging to go to a file or Graylog.

    """
    def __init__(self, logger=logging.getLogger(None),
                 log_format='%(asctime)s %(levelname)s %(message)s',
                 level=None):
        self.log_format = log_format
        self.logger = logger
        if level is not None:
            self.logger.setLevel(level)
            self.level = level

    def config_handler(self, handler):
        if self.log_format is not None:
            formatter = logging.Formatter(self.log_format)
            handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        return handler

    def config_stream(self, stdout_stream, stderr_stream=None):
        out = logging.StreamHandler(stdout_stream)
        if stderr_stream is not None:
            err = logging.StreamHandler(stderr_stream)
            err.addFilter(LogLevelSetFilter({logging.ERROR}))
            out.addFilter(LogLevelSetFilter(
                {logging.WARNING, logging.INFO, logging.DEBUG}))
            self.config_handler(err)
        self.config_handler(out)

    def config_buffer(self):
        log_stream = StringIO()
        self.config_stream(log_stream)
        return log_stream

    def config_file(self, file_name):
        return self.config_handler(logging.FileHandler(file_name))

    def config_basic(self):
        logging.basicConfig(format=self.log_format, level=self.level)

    def capture(self,
                stdout_logger=logging.getLogger('STDOUT'),
                stderr_logger=logging.getLogger('STDERR')):
        if stdout_logger is not None:
            sys.stdout = LoggerStream(stdout_logger, logging.INFO)
        if stderr_logger is not None:
            sys.stderr = LoggerStream(stderr_logger, logging.INFO)


class loglevel(object):
    """Object used with a ``with`` scope that sets the logging level temporarily
    and sets it back.

    Example::

        with loglevel(__name__):
            logger.debug('test')

        with loglevel(['zensols.persist', 'zensols.config'], init=True):
            logger.debug('test')

    """
    def __init__(self, name: Union[List[str], str, None] = '',
                 level: int = logging.DEBUG, init: Union[bool, int] = None,
                 enable: bool = True):
        """Configure the temporary logging setup.

        :param name: the name of the logger to set, or if a list is passed,
                     configure all loggers in the list; if a string, configure
                     all logger names split on spaces; if ``None`` or
                     ``False``, do not configure anything (handy for REPL
                     prototyping); default to the root logger to log everything

        :param level: the logging level, which defaults to :obj:`logging.DEBUG`

        :param init: if not ``None``, initialize logging with
                     :func:`logging.basicConfig` using the given level or
                     ``True`` to use :obj:`logging.WARNING`

        :param enable: if ``False``, disable any logging configuration changes
                       for the block

        """
        if name is None or not name:
            name = ()
        elif isinstance(name, str):
            name = name.split()
        if enable:
            self.loggers = tuple(map(logging.getLogger, name))
        else:
            self.loggers = ()
        self.initial_levels = tuple(map(lambda lg: lg.level, self.loggers))
        self.level = level
        if init is not None and enable:
            if init is True:
                init = logging.WARNING
            logging.basicConfig(level=init)

    def __enter__(self):
        for lg in self.loggers:
            lg.setLevel(self.level)

    def __exit__(self, type, value, traceback):
        for lg, lvl in zip(self.loggers, self.initial_levels):
            lg.setLevel(lvl)


def add_logging_level(level_name, level_num: int, method_name: str = None):
    """Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `level_name` becomes an attribute of the `logging` module with the value
    `level_num`. `method_name` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `method_name` is not specified, `level_name.lower()`
    is used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present.

    See `Stack Overflow`_ for attribution.

    .. Stack Overflow: http://stackoverflow.com/a/13638084/2988730

    """
    import logging

    if level_num is None:
        level_num = logging.DEBUG - 5
    if method_name is None:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError(f'{level_name} already defined in logging module')
    if hasattr(logging, method_name):
        raise AttributeError(f'{method_name} already defined in logging module')
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(f'{method_name} already defined in logger class')

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, logForLevel)
    setattr(logging, method_name, logToRoot)


def add_trace_level():
    """Add a ``logging.TRACE`` logging level."""
    level_name = 'TRACE'
    if not hasattr(logging, level_name):
        add_logging_level(level_name, logging.DEBUG - 5)
