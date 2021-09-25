"""Main entry point for applications that use the :mod:`.app` API.

"""
__author__ = 'Paul Landes'

from typing import List, Dict, Any, Union, Type, Optional, Tuple
from dataclasses import dataclass, field
import sys
import logging
import inspect
from io import TextIOBase
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import DictionaryConfig
from zensols.cli import ActionResult, ApplicationFactory
from . import LogConfigurator

logger = logging.getLogger(__name__)


@dataclass
class CliHarness(object):
    """A utility class to automate the creation of execution of the
    :class:`.Application` from either the command line or a Python REPL.

    """
    src_dir_name: str = field(default='src')
    """The directory (relative to :obj:`root_dir` to add to the Python path
    containing the source files.

    """

    package_resource: Union[str, PackageResource] = field(default='app')
    """The application package resource.

    :see: :obj:`.ApplicationFactory.package_resource`

    """

    app_config_resource: Union[str, TextIOBase] = field(
        default='resources/app.conf')
    """The relative resource path to the application's context.  If set as an
    instance of :class:`io.TextIOBase` then read from that resource instead of
    trying to find a resource file.

    :see: :obj:`.ApplicationFactory.app_config_resource`

    """

    app_config_context: Dict[str, Dict[str, str]] = field(default_factory=dict)
    """More context given to the application context on app creation."""

    root_dir: Path = field(default=None)
    """The entry point directory where to make all files relative.  If not given,
    it is resolved from the parent of the entry point program path in the
    (i.e. :obj:`sys.argv`) arguments.

    """

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

    def configure_logging(self, *args, **kwargs):
        """Convenience method to configure the logging package system for early stage
        (bootstrap) debugging.  However, the "right" way to configure logging
        is in the application configuration.

        The arguments provided are given to the initializer of
        :class:`.LogConfigurator`, which is then used to configure the logging
        system.

        """
        log_conf = LogConfigurator(*args, **kwargs)
        log_conf.config()

    def _create_context(self, root_dir: Path) -> Dict[str, Dict[str, str]]:
        ctx = dict(self.app_config_context)
        ctx['appenv'] = {'root_dir': str(root_dir)}
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating initial context with {ctx}')
        return ctx

    def _create_cli(self, root_dir: Path, factory_kwargs: Dict[str, Any]) \
            -> ApplicationFactory:
        ctx = self._create_context(root_dir)
        dconf = DictionaryConfig(ctx)
        return self.app_factory_class(
            package_resource=self.package_resource,
            app_config_resource=self.app_config_resource,
            children_configs=(dconf,), **factory_kwargs)

    def create_application_factory(self, args: List[str] = (),
                                   **factory_kwargs: Dict[str, Any]) -> \
            Tuple[Tuple[str], ApplicationFactory]:
        """Create and return the application factory.

        :param args: the command line arguments as given from :obj:`sys.argv`,
                     including the program name

        :param factory_kwargs: arguments passed to :class:`.ApplicationFactory`

        :return: the application factory on which to call
                 :meth:`.ApplicationFactory.invoke`

        """
        entry_path = None
        if len(args) > 0:
            args = args[1:]
            if len(args) > 1:
                entry_path = Path(args[0])
        if entry_path is None:
            entry_path = Path('.')
        if self.root_dir is None:
            root_dir = entry_path.parent
        else:
            root_dir = self.root_dir
        src_path = root_dir
        if self.src_dir_name is not None:
            src_path = src_path / self.src_dir_name
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'adding source path: {src_path} to python path')
        sys.path.append(str(src_path))
        return self._create_cli(root_dir, factory_kwargs)

    def invoke(self, args: List[str] = sys.argv,
               **factory_kwargs: Dict[str, Any]) -> Any:
        """Invoke the application.

        :param args: the command line arguments without the first argument (the
                     program name)

        :param factory_kwargs: arguments given to the command line factory

        """
        cli: ApplicationFactory = self.create_application_factory(
            args, **factory_kwargs)
        return cli.invoke(args[1:])

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


@dataclass
class NotebookHarness(object):
    """A harness used in Jupyter notebooks.  This class has default configuration
    useful to having a single directory with one or more notebooks off the
    project root ditectory.

    For this reason :obj:`root_dir` is the parent directory, which is used to
    add :obj:`src_dir_name` to the Python path.

    """
    package_resource: Union[str, PackageResource] = field(default='app')
    """The application package resource.

    :see: :obj:`.ApplicationFactory.package_resource`

    """

    app_config_resource: str = field(default='resources/app.conf')
    """The relative resource path to the application's context."""

    root_dir: Union[Path, str] = field(default=Path('..'))
    """The entry point directory where to make all files relative.  If not given,
    it is resolved from the parent of the entry point program path in the
    (i.e. :obj:`sys.argv`) arguments.

    """

    src_dir_name: Union[Path, str] = field(default=Path('src/python'))
    """The directory (relative to :obj:`root_dir`) to add to the Python path
    containing the source files.

    """

    def __post_init__(self):
        if isinstance(self.root_dir, str):
            self.root_dir = Path(self.root_dir)
        self._init_cli()

    def _init_cli(self):
        self.cli = CliHarness(
            package_resource=self.package_resource,
            app_config_resource=f'{self.root_dir}/{self.app_config_resource}',
            src_dir_name=self.src_dir_name,
            root_dir=self.root_dir,
        )
        self.application_factory = self.cli.create_application_factory()
        self.set_browser_width()

    @staticmethod
    def set_browser_width(width: int = 95):
        """Use the entire width of the browser to create more real estate.

        :param width: the width as a percent (``[0, 100]``) to use as the width
                      in the notebook

        """
        from IPython.core.display import display, HTML
        html = f'<style>.container {{ width:{width}% !important; }}</style>'
        display(HTML(html))

    def __call__(self, args: str) -> Any:
        return self.application_factory.get_instance(args)
