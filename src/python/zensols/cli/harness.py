"""Main entry point for applications that use the :mod:`.app` API.

"""
__author__ = 'Paul Landes'

from typing import List, Dict, Any, Union, Type, Optional
from dataclasses import dataclass, field
import sys
import logging
import inspect
from io import TextIOBase
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import DictionaryConfig
from zensols.cli import ActionResult, ApplicationFactory

logger = logging.getLogger(__name__)


@dataclass
class CliHarness(object):
    """A utility class to automate the creation of execution of the
    :class:`.Application` from either the command line or a Python REPL.

    """
    src_dir_name: str = field(default='src')
    """The directory to add to the Python path containing the source files."""

    package_resource: Union[str, PackageResource] = field(default='app')
    """The application package resource

    :see: :obj:`.ApplicationFactory.package_resource`

    """

    app_config_resource: Union[str, TextIOBase] = field(
        default='resources/app.conf')
    """The relative resource path to the application's context.

    :see: :obj:`.ApplicationFactory.app_config_resource`

    """

    app_config_context: Dict[str, Dict[str, str]] = field(default_factory=dict)
    """More context given to the application context on app creation."""

    app_factory_class: Type[ApplicationFactory] = field(
        default=ApplicationFactory)
    """The application factory used to create thye application."""

    proto_args: Union[str, List[str]] = field(default_factory=list)
    """The command line arguments."""

    proto_factory_kwargs: Dict[str, Any] = field(default_factory=dict)
    """Factory keyword arguments given to the :class:`.ApplicationFactory`."""

    proto_header: str = field(default='--> prototype')
    """Printed for each invocation of the prototype command line.  This is handy
    when running in environments such as Emacs REPL to clarify the invocation
    method.

    """

    log_format: str = field(default='%(asctime)-15s [%(name)s] %(message)s')
    """The log formatting used in :meth:`configure_logging`."""

    @property
    def invoke_method(self) -> str:
        """Return how the program was invoked.

        :return: one of ``eval`` for re-evaluating the file, ``repl`` from the
                 REPL or ``main`` for invocation from the main command line

        """
        meth = None
        finf: inspect.FrameInfo = inspect.stack()[-1]
        mod_name = finf.frame.f_globals['__name__']
        if mod_name == '__main__':
            if finf.filename == '<stdin>':
                meth = 'repl'
            elif finf.filename == '<string>':
                meth = 'eval'
        meth = 'main' if meth is None else meth
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'module name: {mod_name}, file: {finf.filename}, ' +
                         f'method: {meth}')
        return meth

    def configure_logging(self, level: int = logging.INFO):
        """Convenience method to configure the logging package system for early stage
        (bootstrap) debugging.  However, the "right" way to configure logging
        is in the application configuration.

        """
        fmt = '%(asctime)-15s [%(name)s] %(message)s'
        logging.basicConfig(format=fmt, level=level)

    def _create_context(self, root_dir: Path) -> Dict[str, Dict[str, str]]:
        ctx = dict(self.app_config_context)
        ctx['appenv'] = {'root_dir': str(root_dir)}
        return ctx

    def _create_cli(self, entry_path: Path, factory_kwargs: Dict[str, Any]) \
            -> ApplicationFactory:
        ctx = self._create_context(entry_path.parent)
        dconf = DictionaryConfig(ctx)
        return self.app_factory_class(
            package_resource=self.package_resource,
            app_config_resource=self.app_config_resource,
            children_configs=(dconf,), **factory_kwargs)

    def invoke(self, args: List[str] = sys.argv,
               **factory_kwargs: Dict[str, Any]) -> Any:
        """Invoke the application.

        :param args: the command line arguments without the first argument (the
                     program name)

        :param factory_kwargs: arguments given to the command line factory

        """
        entry_path = None
        if len(args) > 0:
            args = args[1:]
            if len(args) > 1:
                entry_path = Path(args[0])
        if entry_path is None:
            entry_path = Path('.')
        src_path = entry_path.parent
        if self.src_dir_name is not None:
            src_path = src_path / self.src_dir_name
        sys.path.append(str(src_path))
        cli: ApplicationFactory = self._create_cli(entry_path, factory_kwargs)
        return cli.invoke(args)

    def _proto(self, args: List[str], **factory_kwargs: Dict[str, Any]):
        """Invoke the prototype.

        :param args: the command line arguments without the first argument (the
                     program name)

        :param factory_kwargs: arguments given to the command line factory

        """
        args = ['_'] + args
        return self.invoke(args, **factory_kwargs)

    def proto(self):
        """Invoke the prototype using :obj:`proto_args` and
        :obj:`proto_factory_kwargs`.

        """
        if self.proto_header is not None:
            print(self.proto_header)
        args = self.proto_args
        args = args.split() if isinstance(args, str) else args
        try:
            return self._proto(args, **self.proto_factory_kwargs)
        except SystemExit as e:
            print(f'exit: {e}')

    def run(self) -> Optional[ActionResult]:
        """The command line script entry point."""
        invoke_method = self.invoke_method
        if invoke_method == 'main':
            # when running from a shell, run the CLI entry point
            return self.invoke()
        elif invoke_method == 'repl':
            # otherwise, assume a Python REPL and run the prototyping method
            return self.proto()
        else:
            logger.debug('skipping re-entry from interpreter re-evaluation')
