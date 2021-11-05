#!/usr/bin/env python

from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from io import StringIO
from zensols.util import Executor
from zensols.cli import ApplicationFactory, CliHarness

logger = logging.getLogger(__name__)


CONFIG = """
# configure the command line
[cli]
class_name = zensols.cli.ActionCliManager
apps = list: app

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


class FsInfoApplicationFactory(ApplicationFactory):
    """The application factory creates instances of :class:`.Application` (defined
    above).  It also provides the package for which it belongs and the
    configuration (given above).

    """
    def __init__(self, *args, **kwargs):
        kwargs.update(dict(package_resource='fsinfo',
                           app_config_resource=StringIO(CONFIG)))
        super().__init__(*args, **kwargs)


# the name check for main isn't needed when the application class is defined in
# a separate file/module than the entry point
if __name__ == '__main__':
    # create the CLI harness, which simplifies the process of executing the
    # application
    harness = CliHarness(app_factory_class=FsInfoApplicationFactory)
    # configure logging for this module to be at level info for the executor
    harness.configure_logging(loggers={'fsinfo': 'info'},
                              format='%%(message)s')
    # run the application based on the command line argument
    res = harness.run().result
    # the result is what's returned from the method invoked mapped by the
    # action given on the command line
    logger.debug(f'exit: {res}')
