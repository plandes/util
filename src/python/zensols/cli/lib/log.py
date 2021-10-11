"""A first pass application to configure the :mod:`logging` system.

"""
__author__ = 'Paul Landes'

from typing import Dict, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from logging import Logger
from pathlib import Path
from .. import ActionCliError, ApplicationError

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Set of configurable log levels on the command line.  Note that we don't
    include all so as to not overwhelm the help usage.

    """
    debug = logging.DEBUG
    info = logging.INFO
    warn = logging.WARNING
    err = logging.ERROR


@dataclass
class LogConfigurator(object):
    """A simple log configuration utility.

    """
    CLI_META = {'first_pass': True,  # not a separate action
                # don't add the '-l' as a short option
                'option_overrides': {'level': {'short_name': None}},
                # we configure this class, but use a better naming for
                # debugging
                'mnemonic_overrides': {'config': 'log'},
                'mnemonic_includes': {'config'},
                # only set 'level' as a command line option so we can configure
                # the rest in the application context.
                'option_includes': {'level'}}
    """Command line meta data to avoid having to decorate this class in the
    configuration.  Given the complexity of this class, this configuration only
    exposes the parts of this class necessary for the CLI.

    """

    log_name: str = field(default=None)
    """The log name space."""

    default_level: LogLevel = field(default=None)
    """The level to set the root logger."""

    level: LogLevel = field(default=None)
    """The level to set the application logger."""

    default_app_level: LogLevel = field(default=LogLevel.info)
    """The default log level to set the applicatiohn logger when not given on the
    command line.

    """

    config_file: Path = field(default=None)
    """If provided, configure the log system with this configuration file."""

    format: str = field(default=None)
    """The format string to use for the logging system."""

    loggers: Dict[str, Union[str, LogLevel]] = field(default=None)
    """Additional loggers to configure."""

    debug: bool = field(default=False)
    """Print some logging to standard out to debug this class."""

    def __post_init__(self):
        if ((self.default_level is not None) or (self.format is not None)) \
           and (self.config_file is not None):
            raise ActionCliError(
                "Cannot set 'default_level' or 'format' " +
                "while setting a log configuration file 'config_file'")
        if self.default_level is None:
            self.default_level = LogLevel.warn

    def _to_level(self, name: str, level: Any) -> int:
        if isinstance(level, LogLevel):
            level = level.value
        elif isinstance(level, str):
            obj = LogLevel.__members__.get(level)
            if obj is None:
                raise ApplicationError(f'No such level for {name}: {level}')
            level = obj.value
        if not isinstance(level, int):
            raise ActionCliError(f'Unknown level: {level}({type(level)})')
        return level

    def _debug(self, msg: str):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(msg)
        if self.debug:
            print(msg)

    def _config_file(self):
        import logging.config
        self._debug(f'configuring from file: {self.config_file}')
        logging.config.fileConfig(self.config_file,
                                  disable_existing_loggers=False)

    def _config_basic(self):
        self._debug(f'configuring root logger to {self.default_level}')
        level: int = self._to_level('default', self.default_level)
        params = {'level': level}
        if self.format is not None:
            params['format'] = self.format.replace('%%', '%')
        self._debug(f'config log system with level {level} ' +
                    f'({self.default_level})')
        logging.basicConfig(**params)

    def config(self):
        """Configure the log system.

        """
        modified_logger: Logger = None
        if self.config_file is not None:
            self._config_file()
        else:
            self._config_basic()
        if self.log_name is not None:
            app_level = self.default_app_level \
                if self.level is None else self.level
            level: int = self._to_level('app', app_level)
            self._debug(f'setting logger {self.log_name} to {level} ' +
                        f'({app_level})')
            modified_logger = logging.getLogger(self.log_name)
            modified_logger.setLevel(level)
        if self.loggers is not None:
            for name, level in self.loggers.items():
                level = self._to_level(name, level)
                assert isinstance(level, int)
                self._debug(f'setting logger: {name} -> {level}')
                modified_logger = logging.getLogger(name)
                modified_logger.setLevel(level)
        return modified_logger

    def __call__(self):
        return self.config()
