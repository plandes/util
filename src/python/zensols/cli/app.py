from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Dict, Iterable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import sys
from itertools import chain
from pathlib import Path
from zensols.introspect import Class, ClassMethod, ClassField, ClassMethodArg
from zensols.persist import persisted
from zensols.util import PackageResource
from zensols.config import (
    Dictable, Configurable, ConfigFactory,
    ImportIniConfig, DictionaryConfig, ImportConfigFactory,
)
from . import (
    ActionCliError,
    ActionCliManager, ActionCli, ActionCliMethod, ActionMetaData,
    CommandAction, CommandActionSet, CommandLineConfig, CommandLineParser,
 )

logger = logging.getLogger(__name__)


@dataclass
class Action(Dictable):
    """Contains everything needed to invoke an action invoked from the command
    line.  A list of these, one per executable action, is used by
    :class:`.Application` and invoked in order on the target application
    class(es).

    """
    WRITABLE__DESCENDANTS = True

    command_action: CommandAction = field()
    """The result of the command line parsing of the action.  It contains the data
    parsed on a per action level.

    """

    cli: ActionCli = field()
    """Command line interface of the action meta data."""

    meta_data: ActionMetaData = field()
    """An action represents a link between a command line mnemonic *action* and a
    method on a class to invoke.

    """

    method_meta: ClassMethod = field()
    """The metadata of the method to use for the invocation of the action.

    """

    @property
    @persisted('_name')
    def name(self) -> str:
        """The name of the action, which is the form:

          ``<action's section name>.<meta data's name>``

        """
        return f'{self.cli.section}.{self.meta_data.name}'

    @property
    def section(self) -> str:
        """The section from which the :class:`.ActionCli` was created."""
        return self.cli.section

    @property
    def class_meta(self) -> Class:
        """The meta data of the action, which comes from :class:`.ActionCli`.

        """
        return self.cli.class_meta

    @property
    def class_name(self) -> str:
        """Return the class name of the target application instance.

        """
        return self.class_meta.name

    @property
    def method_name(self) -> str:
        """The method to invoke on the target application instance class.

        """
        return self.method_meta.name

    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        return map(lambda f: (f, f),
                   'section class_name method_name command_action'.split())

    def __str__(self):
        return (f'{self.section} ({self.class_name}.{self.method_name}): ' +
                f'<{self.command_action}>')

    def __repr__(self):
        return self.__str__()


@dataclass
class ActionResult(Dictable):
    """The results of a single method call to an :class:`.Action` instance.

    """
    action: Action = field()
    """The action that was used to generate the result."""

    instance: Any = field()
    """The application instance."""

    result: Any = field()
    """The results returned from the invocation on the application instance."""

    @property
    def name(self) -> str:
        return self.action.name

    def __call__(self):
        return self.result


@dataclass
class ApplicationResult(Dictable):
    """The results of an application invocation with :meth:`.Application.invoke`.

    """
    action_results: Tuple[ActionResult]

    @property
    @persisted('_by_name')
    def by_name(self) -> Dict[str, ActionResult]:
        return {a.name: a for a in self}

    @property
    def second_pass_result(self) -> ActionResult:
        sec_pass = tuple(filter(lambda r: not r.action.meta_data.first_pass,
                                self.action_results))
        assert(len(sec_pass) == 1)
        return sec_pass[0]

    def __call__(self) -> ActionResult:
        return self.second_pass_result

    def __getitem__(self, index: int) -> ActionResult:
        return self.action_results[index]

    def __len__(self) -> int:
        return len(self.action_results)


class ApplicationObserver(ABC):
    """Extended by application targets to get call backs and information from the
    controlling :class:`.Application`.

    """
    @abstractmethod
    def _application_created(self, app: Application, action: Action):
        """Called just after the application target is created.

        :param app: the application that created the application target

        """
        pass


@dataclass
class Application(Dictable):
    """An invokable application created using command line and application context
    data.  This class creates an instance of the *target application instance*,
    then invokes the corresponding action method.

    """
    WRITABLE__DESCENDANTS = True

    config_factory: ConfigFactory = field(repr=False)
    """The factory used to create the application and its components."""

    factory: ApplicationFactory = field(repr=False)
    """The factory that created this application."""

    actions: Tuple[Action] = field()
    """The list of actions to invoke in order."""

    def _create_instance(self, action: Action) -> Any:
        """Instantiate the in memory application instance using the CLI input gathered
        from the user and the configuration.

        """
        cmd_opts: Dict[str, Any] = action.command_action.options
        const_params: Dict[str, Any] = {}
        sec = action.section
        # gather fields
        field: ClassField
        for f in action.class_meta.fields.values():
            val: str = cmd_opts.get(f.name)
            # set the field used to create the app target instance if given by
            # the user on the command line
            if val is None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f'no param for action <{action}>: {f.name}')
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f'field map: {sec}:{f.name} -> {val} ({f.dtype})')
                const_params[f.name] = val
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating {sec} with {const_params}')
        # create the instance using the configuration factory
        inst = self.config_factory.instance(sec, **const_params)
        if isinstance(inst, ApplicationObserver):
            inst._application_created(self, action)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'created instance {inst}')
        return inst

    def _get_meth_params(self, action: Action, meth_meta: ClassMethod) -> \
            Tuple[Tuple[Any], Dict[str, Any]]:
        """Get the method argument and keyword arguments gathered from the user input
        and configuration.

        :return: a tuple of the positional arguments (think ``*args``) followed
                 by the keyword arguments map (think ``**kwargs`)

        """
        cmd_opts: Dict[str, Any] = action.command_action.options
        meth_params: Dict[str, Any] = {}
        pos_args = action.command_action.positional
        pos_arg_count: int = 0
        arg: ClassMethodArg
        for arg in meth_meta.args:
            if arg.is_positional:
                pos_arg_count += 1
            else:
                name: str = arg.name
                if name not in cmd_opts:
                    raise ActionCliError(
                        f'no such option {name} parsed from CLI for ' +
                        f'method from {cmd_opts}: {meth_meta.name}')
                val: str = cmd_opts.get(name)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'meth map: {meth_meta.name}.{name} -> {val}')
                meth_params[name] = val
        if pos_arg_count != len(pos_args):
            raise ActionCliError(f'method {meth_meta.name} expects ' +
                                 f'{pos_arg_count} but got {len(pos_args)}')
        return pos_args, meth_params

    def invoke(self) -> ApplicationResult:
        """Invoke the application and return the results.

        """
        results: List[ActionResult] = []
        action: Action
        for action in self.actions:
            inst = self._create_instance(action)
            meth_meta: ClassMethod = action.method_meta
            pos_args, meth_params = self._get_meth_params(action, meth_meta)
            meth = getattr(inst, meth_meta.name)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'invoking {meth}')
            res: Any = meth(*pos_args, **meth_params)
            results.append(ActionResult(action, inst, res))
        return ApplicationResult(tuple(results))


@dataclass
class ApplicationFactory(object):
    """Boots the application context from the command line.  This first loads
    resource ``resources/app.conf`` from this package, then adds
    :obj:`app_config_resource` from the application package of the client.

    """
    UTIL_PACKAGE = 'zensols.util'
    """The package name of *this* utility package."""

    package_resource: PackageResource = field()
    """Package resource (i.e. zensols.someappname)."""

    app_config_resource: str = field(default='resources/app.conf')
    """The relative resource path to the application's context."""

    @classmethod
    def instance(cls, package_name: str, *args, **kwargs) -> \
            ApplicationFactory:
        """"A convenience method to create a factory instance by first converting the
        package name string to a :class:`.PackageResoure`.

        :param package_name: used to create the :obj:`package_resource`

        :param app_config_resource: see class docs

        """
        pres = PackageResource(package_name)
        return cls(pres, *args, **kwargs)

    def _create_application_context(self, parent_context: Path,
                                    app_context: Path) -> Configurable:
        """Factory method to create the application context from the :mod:`cli`
        resource (parent) context and a path to the application specific
        (child) context.

        :param parent_context: the :mod:`cli` root level context path

        :param app_context: the application child context path

        """
        app_conf = DictionaryConfig(
            {'import_app': {'config_file': str(app_context.absolute()),
                            'type': 'ini'}})
        return ImportIniConfig(parent_context, children=(app_conf,))

    def _create_config_factory(self, config: Configurable) -> ConfigFactory:
        """Factory method to create the configuration factory from the application
        context created in :meth:`_get_app_context`.

        """
        return ImportConfigFactory(config)

    def _get_app_context(self, app_context: Path) -> Configurable:
        """Create the initial *bootstrap* app config.

        :param app_context: the path to the app specific application context
                            configuration file

        """
        pres = PackageResource(self.UTIL_PACKAGE)
        res: str = self.app_config_resource
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'looking up resource: {res} in {pres}')
        parent_context: Path = pres.get_path(res)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('loading zensols.util app context parent ' +
                         f'{parent_context.absolute()} with child app ' +
                         f'context {app_context.absolute()}')
        if not parent_context.exists():
            # this should never not happen
            raise ValueError(f'no application context found: {parent_context}')
        return self._create_application_context(parent_context, app_context)

    @persisted('_resources')
    def _create_resources(self) -> \
            Tuple[ConfigFactory, ActionCliManager, CommandLineParser]:
        """Create the config factory, the command action line manager, and command line
        parser resources.  The data is cached and use in property getters.

        """
        path: Path = self.package_resource.get_path(self.app_config_resource)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'path to app specific context: {path.absolute()}')
        if not path.exists():
            raise ActionCliError(
                f"application context resource '{self.app_config_resource}' " +
                f'not found in {self.package_resource}')
        config: Configurable = self._get_app_context(path)
        fac: ConfigFactory = self._create_config_factory(config)
        cli_mng: ActionCliManager = fac(ActionCliManager.SECTION)
        actions: Tuple[ActionMetaData] = tuple(chain.from_iterable(
            map(lambda a: a.meta_datas, cli_mng.actions.values())))
        config = CommandLineConfig(actions)
        parser = CommandLineParser(config, self.package_resource.version)
        return fac, cli_mng, parser

    @property
    def parser(self) -> CommandLineParser:
        """Used to parse the command line.

        """
        return self._create_resources()[2]

    @property
    def cli_manager(self) -> ActionCliManager:
        """The manager that creates the action based CLIs.

        """
        return self._create_resources()[1]

    def _parse(self, args: List[str]) -> Tuple[Action]:
        """Parse the command line.

        """
        fac, cli_mng, parser = self._create_resources()
        actions: List[Action] = []
        action_set: CommandActionSet = parser.parse(args)
        action_clis: Dict[str, ActionCli] = cli_mng.actions_by_meta_data_name
        caction: CommandAction
        # create an action (coupled with meta data) for each command line
        # parsed action
        for caction in action_set.actions:
            name = caction.meta_data.name
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'action name: {name}')
            action_cli: ActionCli = action_clis[name]
            acli_meth: ActionCliMethod = action_cli.methods[name]
            action: Action = Action(
                caction, action_cli,
                acli_meth.action_meta_data, acli_meth.method)
            actions.append(action)
        return actions

    def create(self, args: List[str] = sys.argv[1:]) -> Application:
        """Create the action CLI application.

        :raises ActionCliError: for any missing data or misconfigurations

        """
        fac, cli_mng, parser = self._create_resources()
        actions: Tuple[Action] = self._parse(args)
        return Application(fac, self, actions)
