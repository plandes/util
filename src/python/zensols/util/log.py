from dataclasses import dataclass, field
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


class LogConfigurerLegacy(object):
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


@dataclass
class LogConfigurator(object):
    """A simple log configuration utility.

    """
    log_name: str = field(default=None)
    """The log name space."""

    level: str = field(default='info')
    """The level to set the application logger."""

    default_level: str = field(default='warning')
    """The level to set the root logger."""

    def config(self):
        msg = (f'configuring root logger to {self.default_level} and ' +
               f'{self.log_name} to {self.level}')
        print(msg)
        logging.basicConfig(level=self.default_level)
        if self.log_name is not None:
            logging.getLogger(self.log_name).setLevel(self.level)


class loglevel(object):
    """Object used with a ``with`` scope that sets the logging level temporarily
    and sets it back.

    Example::
        with loglevel(__name__):
            logger.debug('test')

    """
    def __init__(self, name: str, level: int = logging.DEBUG,
                 init: int = None):
        """Initialize.

        :param name: the name of the logger to set

        :param level: the logging level, which defaults to :obj:`logging.DEBUG`

        :param init: if not ``None``, initialize logging with
                     :func:`logging.basicConfig` using the given level or
                     ``True`` to use :obj:`logging.WARNING`

        """
        self.logger = logging.getLogger(name)
        self.initial_level = self.logger.level
        self.level = level
        if init is not None:
            if init is True:
                init = logging.WARNING
            logging.basicConfig(level=init)

    def __enter__(self):
        self.logger.setLevel(self.level)

    def __exit__(self, type, value, traceback):
        self.logger.setLevel(self.initial_level)
