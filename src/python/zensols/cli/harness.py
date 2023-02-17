"""Main entry point for applications that use the :mod:`.app` API.

"""
__author__ = 'Paul Landes'

from typing import List, Dict, Any, Union, Type, Optional, Tuple, ClassVar
from dataclasses import dataclass, field
import sys
import os
import logging
import inspect
from io import TextIOBase
from pathlib import Path
from zensols.util import PackageResource, APIError
from zensols.config import DictionaryConfig, ConfigFactory
from zensols.config import (
    ModulePrototype, ImportConfigFactoryModule, ImportConfigFactory
)
from zensols.introspect import ClassImporter
from zensols.cli import (
    ApplicationError, ApplicationFailure, Action, ActionResult, OptionMetaData,
    Application, ApplicationResult, ApplicationFactory, ConfigurationImporter
)
from . import LogConfigurator

logger = logging.getLogger(__name__)


@dataclass
class ConfigFactoryAccessor(object):
    """Return an instance from a :class:`.ConfigFactory`, which is useful for
    creating harnesses and accessing application context configured instances.

    *Important*: if configured to access an application class in the application
    context, you will need to remove the entry from the removes in the ``cli``
    seciton of the ``app.conf`` file.

    """
    LONG_NAME = 'add_ConfigFactoryAccessor_to_app_config'
    CLI_META = {'option_includes': {},
                'mnemonic_overrides': {'access': LONG_NAME},
                'is_usage_visible': False}

    config_factory: ConfigFactory = field()
    """The parent configuration factory that is returned when accessed."""

    def access(self) -> ConfigFactory:
        """Return the configuration factory."""
        return self.config_factory


@dataclass
class _HarnessEnviron(object):
    """A context to help the harness do things like relocate the environment
    (i.e. root directory that has data and resource files).

    """
    args: List[str]
    src_path: Path
    root_dir: Path
    app_config_resource: Union[str, TextIOBase]


@dataclass
class CliHarness(object):
    """A utility class to automate the creation of execution of the
    :class:`.Application` from either the command line or a Python REPL.

    """
    src_dir_name: str = field(default=None)
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
    app_factory_class: Union[str, Type[ApplicationFactory]] = field(
        default=ApplicationFactory)
    """The application factory used to create thye application."""

    relocate: bool = field(default=True)
    """Whether or not to make :obj:`source_dir_name` and :obj:`app_config_resource`
    relative to :obj:`root_dir` (when non-``None``).  This should be set to
    ``False`` when used to create an application that is installed (i.e. with
    pip).

    """
    proto_args: Union[str, List[str]] = field(default_factory=list)
    """The command line arguments."""

    proto_factory_kwargs: Dict[str, Any] = field(default_factory=dict)
    """Factory keyword arguments given to the :class:`.ApplicationFactory`."""

    proto_header: str = field(default=None)
    """Printed for each invocation of the prototype command line.  This is handy
    when running in environments such as Emacs REPL to clarify the invocation
    method.

    """
    log_format: str = field(default='%(asctime)-15s [%(name)s] %(message)s')
    """The log formatting used in :meth:`configure_logging`."""

    no_exit: bool = field(default=False)
    """If ``True`` do not exist the program when :class:`SystemExit` is raised.

    """
    def __post_init__(self):
        if self.root_dir is not None:
            if not self.root_dir.is_dir():
                raise ApplicationError(
                    f'No such root directory: {self.root_dir}')
            self.add_sys_path(self.root_dir)

    @staticmethod
    def add_sys_path(to_add: Path):
        """Add to the Python system path if not already.

        :param to_add: the path to test and add

        """
        def canon(p: Path):
            return p.expanduser().resolve().absolute()

        spath: str
        to_add = canon(to_add)
        if not any(map(lambda p: canon(Path(p)) == to_add, sys.path)):
            sys.path.append(str(to_add))

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

    def _handle_exit(self, se: SystemExit):
        """Handle attempts to exit the Python interpreter.  This default implementation
        simplly prints the error if :obj:`no_exit` is ``True``.

        :param se: the error caught

        :raises: SystemExit if :obj:`no_exit` is ``False``

        """
        if self.no_exit:
            print(f'exit: {se}')
        else:
            raise se

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

    def _create_context(self, env: _HarnessEnviron) -> \
            Dict[str, Dict[str, str]]:
        ctx = dict(self.app_config_context)
        appenv = ctx.get('appenv')
        if appenv is None:
            appenv = {}
            ctx['appenv'] = appenv
        appenv['root_dir'] = str(env.root_dir)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating initial context with {ctx}')
        return ctx

    def _get_app_factory_class(self) -> Type[ApplicationFactory]:
        if isinstance(self.app_factory_class, str):
            ci = ClassImporter(self.app_factory_class, False)
            cls = ci.get_class()
        else:
            cls = self.app_factory_class
        return cls

    def _relocate_harness_environ(self, args: List[str]) -> _HarnessEnviron:
        """Create a relocated harness environment.

        :param args: all command line arguments as given from :obj:`sys.argv`,
                     including the program name

        """
        entry_path: Path = None
        cur_path = Path('.')
        src_path = None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'args: {args}')
        if len(args) > 0:
            entry_path = Path(args[0]).parents[0]
            args = args[1:]
        if entry_path is None:
            entry_path = cur_path
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'entry path: {entry_path}')
        if self.root_dir is None:
            root_dir = entry_path
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'no root dir, using entry path: {entry_path}')
        else:
            root_dir = entry_path / self.root_dir
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'root dir: {root_dir}')
        if self.src_dir_name is not None:
            src_path = root_dir / self.src_dir_name
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'adding source path: {src_path} to python path')
            self.add_sys_path(src_path)
        app_conf_res: str = self.app_config_resource
        if isinstance(app_conf_res, str):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f'app conf res: {app_conf_res}, entry path: {entry_path}' +
                    f', root_dir: {root_dir}, cur_path: {cur_path}')
            if root_dir != cur_path:
                app_conf_res: Path = root_dir / app_conf_res
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'relative app conf res: {app_conf_res}')
                # absolute paths do not work with package_resource as it
                # removes the leading slash when resolving resource paths
                app_conf_res = Path(os.path.relpath(
                    app_conf_res.resolve(), Path.cwd()))
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'update app config resource: {app_conf_res}')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'args={args}, src_path={src_path}, ' +
                         f'root_dir={root_dir}, app_conf_res={app_conf_res}')
        return _HarnessEnviron(args, src_path, root_dir, app_conf_res)

    def _create_harness_environ(self, args: List[str]) -> _HarnessEnviron:
        """Process paths and configure the Python path necessary to execute the
        application.

        :param args: all command line arguments as given from :obj:`sys.argv`,
                     including the program name

        """
        if self.relocate:
            return self._relocate_harness_environ(args)
        else:
            if len(args) > 0:
                args = args[1:]
            return _HarnessEnviron(
                args, None, Path('.'), self.app_config_resource)

    def _create_app_fac(self, env: _HarnessEnviron,
                        factory_kwargs: Dict[str, Any]) -> ApplicationFactory:
        ctx = self._create_context(env)
        dconf = DictionaryConfig(ctx)
        cls = self._get_app_factory_class()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating {cls}: ' +
                         f'package resource: {self.package_resource}, ' +
                         f'config resource: {env.app_config_resource}, ' +
                         f'context: {ctx}')
        return cls(
            package_resource=self.package_resource,
            app_config_resource=env.app_config_resource,
            children_configs=(dconf,),
            **factory_kwargs)

    def create_application_factory(self, args: List[str] = (),
                                   **factory_kwargs: Dict[str, Any]) -> \
            ApplicationFactory:
        """Create and return the application factory.

        :param args: all command line arguments as given from :obj:`sys.argv`,
                     including the program name

        :param factory_kwargs: arguments passed to :class:`.ApplicationFactory`

        :return: the application factory on which to call
                 :meth:`.ApplicationFactory.invoke`

        """
        env: _HarnessEnviron = self._create_harness_environ(args)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'environ: {env}')
        return self._create_app_fac(env, factory_kwargs)

    def invoke(self, args: List[str] = sys.argv,
               **factory_kwargs: Dict[str, Any]) -> ApplicationResult:
        """Invoke the application using the standard command line arguments.
        This is called from command line entry points.  To invoke from Python
        use :meth:`execute`.

        :param args: all command line arguments including the program name

        :param factory_kwargs: arguments given to the command line factory

        :return: the application results

        """
        cli: ApplicationFactory = self.create_application_factory(
            args, **factory_kwargs)
        try:
            return cli.invoke(args[1:])
        except SystemExit as e:
            self._handle_exit(e)
            return e

    def get_instance(self, args: Union[List[str], str] = '',
                     **factory_kwargs: Dict[str, Any]) -> \
            Union[Any, ApplicationFailure]:
        """Create the invokable instance of the application.

        ;param args: the arguments to the application not including the program
                     name (as it makes no sense in the context of this call);
                     if this is a string, it will be converted to a list by
                     splitting on whitespace; this defaults to the output of
                     :meth:`_get_default_args`

        :param factory_kwargs: arguments passed to :class:`.ApplicationFactory`

        :see: :meth:`.ApplicationFactory.get_instance`

        """
        self.no_exit = True
        if isinstance(args, str):
            args = f'_ {args}'
        else:
            args = ['_'] + args
        cli: ApplicationFactory = self.create_application_factory(
            args, **factory_kwargs)
        if cli.error_handler is None:
            cli.error_handler = ApplicationFailure
        try:
            return cli.get_instance(args[1:])
        except SystemExit as e:
            return self._handle_exit(e)

    def _normalize_args(self, args: Optional[Union[List[str], str]],
                        create_if_none: bool = True) -> List[str]:
        if args is None:
            if create_if_none:
                args = []
        else:
            if isinstance(args, str):
                args = args.split()
            elif not isinstance(args, list):
                raise APIError(
                    f'Expecting argument list of str but got: {args}')
        return args

    def get_config_factory(self, args: Union[List[str], str] = None,
                           throw: bool = True) -> \
            Union[ConfigFactory, ApplicationFailure]:
        """The application configuration factory.

        :param args: additional argument to give to the pseudo command line
                     (i.e. ``-c <configuration file>``)

        :param throw: whether to throw exceptions raised during executing the
                      application; if ``False`` then return an
                      :class:`.ApplicationFailure`

        :return: the configuration factory used to create the application
                 environment and application config or the
                 :class:`.ApplicationFailure` if ``throw`` is ``True``

        """
        inst_args: List[str] = [ConfigFactoryAccessor.LONG_NAME]
        if args is not None:
            args = self._normalize_args(args)
            inst_args.extend(args)
        accessor: ConfigFactoryAccessor = self.get_instance(inst_args)
        if isinstance(accessor, ApplicationFailure):
            if throw:
                raise accessor.exception
            else:
                return accessor
        else:
            return accessor.access()

    def get_application(self, args: Union[List[str], str] = None,
                        throw: bool = True) -> \
            Union[Application, ApplicationFailure]:
        """Get the application from the configuration factory.  For this to
        work, the ``app`` section most not be in the cleanups.  Otherwise the
        framework will remove the section before the call to the configuration
        factory to create it.

        """
        config_factory: Union[ConfigFactory, ApplicationFailure] = \
            self.get_config_factory(args, throw)
        if isinstance(config_factory, ConfigFactory):
            if not 'app' in config_factory.config.sections:
                raise ApplicationError(
                    "No 'app' section in configuration. " +
                    "Remove it from cleanups?")
            return config_factory('app')

    def __getitem__(self, section_name: str) -> Optional[Any]:
        """Index by section name binded application configuration instances.

        :param section_name: the section used to create the instance

        """
        fac: ConfigFactory = self.get_config_factory()
        return fac(section_name)

    def _proto(self, args: Union[List[str], str],
               **factory_kwargs: Dict[str, Any]) -> ApplicationResult:
        """Invoke the prototype.

        :param args: the command line arguments without the first argument (the
                     program name)

        :param factory_kwargs: arguments given to the command line factory

        :return: the application results

        """
        args = ['_'] + self._normalize_args(args)
        self.no_exit = True
        return self.invoke(args, **factory_kwargs)

    def proto(self, args: Union[List[str], str] = None) -> \
            Optional[ApplicationResult]:
        """Invoke the prototype using :obj:`proto_args` and
        :obj:`proto_factory_kwargs`.

        :param args: the command line arguments without the first argument (the
                     program name)

        :return: the application results if it did not try to exit

        """
        if self.proto_header is not None:
            print(self.proto_header)
        args = self.proto_args if args is None else args
        try:
            return self._proto(args, **self.proto_factory_kwargs)
        except SystemExit as e:
            self._handle_exit(e)

    def run(self) -> Optional[ActionResult]:
        """The command line script (i.e. model harness scripts) entry point.

        :return: the application results if it did not exit

        """
        invoke_method = self.invoke_method
        if invoke_method == 'main':
            # when running from a shell, run the CLI entry point
            return self.invoke()
        elif invoke_method == 'repl':
            # otherwise, assume a Python REPL and run the prototyping method
            return self.proto()
        else:
            logger.debug('skipping re-entry from interpreter re-evaluation')

    def execute(self, args: Union[List[str], str] = None) -> \
            Optional[ApplicationResult]:
        """Invoke the application with command line with arguments from other
        Python programs or the REPL.

        :param args: the command line arguments without the first argument (the
                     program name)

        :return: the application results if it did not try to exit

        """
        self.proto_header = None
        self.no_exit = True
        try:
            return self.proto(args)
        except SystemExit as e:
            self._handle_exit(e)

    def __call__(self, args: Union[List[str], str] = None) -> \
            Optional[ApplicationResult]:
        """Invoke using :meth:`execute`."""
        self.execute(args)


@dataclass
class ConfigurationImporterCliHarness(CliHarness):
    """A harness that adds command line argument for the configuration file when
    they are available.  It does this by finding an instance of
    :class:`.ConfigurationImporter` in the command line metadata.  When it
    finds it, if not set from the given set of arguments it:

      1. Uses :obj:`config_path`

      2. Gets the path from the environment variable set using
      :class:`.ConfigurationImporter`

    """
    config_path: Union[str, Path] = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.config_path, str):
            self.config_path = Path(self.config_path)

    def _get_config_path_args(self, env: _HarnessEnviron,
                              app: Application) -> List[str]:
        args: List[str] = []
        capp: Action = tuple(filter(
            lambda a: a.class_meta.class_type == ConfigurationImporter,
            app.first_pass_actions))
        capp = capp[0] if len(capp) > 0 else None
        if capp is not None:
            ci: ConfigurationImporter = app.get_invokable(capp.name).instance
            if ci.config_path is None:
                op: OptionMetaData = capp.command_action.meta_data.options[0]
                lnop: str = f'--{op.long_name}'
                envvar: str = ci.get_environ_var_from_app()
                envval: str = os.environ.get(envvar)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('harness loading config from environment ' +
                                 f"varaibles '{envvar}' = {envval}")
                config_path: Path = None
                if self.config_path is not None:
                    config_path = self.config_path
                elif envval is not None:
                    config_path = Path(envval)
                if config_path is not None:
                    config_path = env.root_dir / config_path
                    args.extend((lnop, str(config_path)))
        return args

    def _update_args(self, args: List[str],
                     **factory_kwargs: Dict[str, Any]) -> \
            Tuple[str, ApplicationFactory]:
        env: _HarnessEnviron = self._create_harness_environ(args)
        app_fac: ApplicationFactory = self._create_app_fac(env, factory_kwargs)
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'creating application {app_fac} with {env.args}')
            app: Application = app_fac.create(env.args)
            args = list(env.args)
            args.extend(self._get_config_path_args(env, app))
            return app_fac, args
        except ApplicationError as ex:
            app_fac._dump_error(ex)

    def invoke(self, args: List[str] = sys.argv,
               **factory_kwargs: Dict[str, Any]) -> Any:
        app_fac, args = self._update_args(args, **factory_kwargs)
        if app_fac is not None:
            return app_fac.invoke(args)

    def get_instance(self, args: Union[List[str], str] = None,
                     **factory_kwargs: Dict[str, Any]) -> Any:
        args = self._normalize_args(args)
        args.insert(0, '_')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'get inst: {args}, factory: {factory_kwargs}')
        app_fac, args = self._update_args(args, **factory_kwargs)
        if app_fac is not None:
            return app_fac.get_instance(args)


@dataclass
class NotebookHarness(CliHarness):
    """A harness used in Jupyter notebooks.  This class has default configuration
    useful to having a single directory with one or more notebooks off the
    project root ditectory.

    For this reason :obj:`root_dir` is the parent directory, which is used to
    add :obj:`src_dir_name` to the Python path.

    """
    factory_kwargs: Dict[str, Any] = field(default_factory=dict)
    """Arguments given to the factory when creating new application instances with
    :meth:`__call__`.

    """
    def __post_init__(self):
        super().__post_init__()
        self._app_factory = None
        self.reset()

    def reset(self):
        """Reset the notebook and recreate all resources.

        """
        self.set_browser_width()
        if self._app_factory is not None:
            self._app_factory.deallocate()
        self._app_factory = self.create_application_factory(
            **self.factory_kwargs)

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
        """Return the invokable instance."""
        return self._app_factory.get_instance(args)


@dataclass
class _ApplicationImportConfigFactoryModule(ImportConfigFactoryModule):
    """A module that creates instance from the context of a *different*
    application.

    The configuration string prototype has the form::

        application(<package name>): <instance section name>

    """
    _NAME: ClassVar[str] = 'application'

    def __post_init__(self):
        self._factories: Dict[str, ConfigFactory] = {}

    def _get_factory(self, proto: ModulePrototype) -> ConfigFactory:
        pkg: str = proto.config_str
        fac: ConfigFactory = self._factories.get(pkg)
        if fac is None:
            harness: CliHarness = CliHarness(package_resource=pkg)
            fac = harness.get_config_factory()
            self._factories[pkg] = fac
        return fac

    def _instance(self, proto: ModulePrototype) -> Any:
        fac: ConfigFactory = self._get_factory(proto)
        return fac(proto.name)


ImportConfigFactory.register_module(_ApplicationImportConfigFactoryModule)
