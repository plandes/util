#!/usr/bin/env python

from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from io import StringIO
from zensols.util import Executor
from zensols.cli import CliHarness, ProgramNameConfigurator

logger = logging.getLogger(__name__)

CONFIG = """
# configure the command line
[cli]
apps = list: log_cli, app

[log_cli]
class_name = zensols.cli.LogConfigurator
format = ${program:name}: %%(message)s
log_name = ${program:name}
level = debug

# create an instance of an executor that uses this module's logger (above)
[executor]
class_name = zensols.util.Executor
logger = eval({'import': ['fsinfo']}): fsinfo.logger

# define the application, whose code is given below
[app]
class_name = fsinfo.Application
executor = instance: executor
"""


class Format(Enum):
    """Used to define a choice for :meth:`.Application.ls`.

    """
    short = auto()
    long = auto()


@dataclass
class Application(object):
    """Toy application example that provides file system information.

    """
    # tell the framework to not treat the executor field as an option
    CLI_META = {'option_excludes': {'executor'}}

    executor: Executor = field()
    """The executor."""

    def ls(self, format: Format = Format.short):
        """List the contents of the directory.

        :param format: the output format

        """
        cmd = ['ls']
        if format == Format.long:
            cmd.append('-l')
        return self.executor(cmd)

    def df(self):
        """Display the amount of disk space available.

        """
        return self.executor('df')

    def echo(self, text: str):
        """Repeat back what is given as text.

        """
        print(text)


if (__name__ == '__main__'):
    # create the CLI harness, which simplifies the process of executing the
    # application
    CliHarness(
        # either a pathlib.Path to where the config is, or for this example,
        # the configuration itself.
        app_config_resource=StringIO(CONFIG),
        # create a Configurable configuration instance and pass as a two level
        # dictionary with the program name
        app_config_context=ProgramNameConfigurator(
            None, default='fsinfo').create_section(),
        # arguments passed when run from the Python REPL
        proto_args='ls -f long',
        # factory keyword arguments when running in the Python REPL, so we
        # don't have to restart after each change
        proto_factory_kwargs={'reload_pattern': '^fsinfo'},
    ).run()
