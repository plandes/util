from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Dict, Iterable, Any, Callable, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import sys
import re
from io import TextIOBase
from itertools import chain
from pathlib import Path
from zensols.introspect import Class, ClassMethod, ClassField, ClassMethodArg
from zensols.persist import (
    persisted, PersistedWork, PersistableContainer, Deallocatable
)
from zensols.util import PackageResource
from zensols.config import (
    ConfigurableFileNotFoundError, Serializer, Dictable,
    Configurable, ConfigFactory, ImportIniConfig, ImportConfigFactory,
)
from . import (
    ActionCliError, DocUtil,
    ActionCliManager, ActionCli, ActionCliMethod, ActionMetaData,
    CommandAction, CommandActionSet, CommandLineConfig, CommandLineParser,
 )

logger = logging.getLogger(__name__)


@dataclass
class Action(Deallocatable, Dictable):
    """An invokable action from the command line the :class:`.Application` class.
    This class combines the user input from the command line with the meta data
    from the Python classes given in the configuration.

    Combined, these two data sources provide a means to execute an action,
    which is conceptually one functionality of the application and literally a
    Python class method.

    The class also is somewhat of a facade allowing a client to access data
    from both sources without needing to know where it comes from via the
    class's properties.

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

    def deallocate(self):
        super().deallocate()
        self._try_deallocate((self.command_action, self.action_cli))

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
    """The results of a single method call to an :class:`.Action` instance.  There
    is one of these per action (both first and second pass) provided in
    :class:`.ApplicationResult`.

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
    """A container class of the results of an application invocation with
    :meth:`.Application.invoke`.  This is keyed by index of the actions given
    in :obj:`actions`.

    """
    action_results: Tuple[ActionResult] = field()
    """Both first and second pass action results.  These are provided in the same
    order for which was executed when the class:`.Application` ran, which is
    that same order provided to the :class:`.ActionCliManager`.

    """

    @property
    @persisted('_by_name')
    def by_name(self) -> Dict[str, ActionResult]:
        """Per action results keyed by action name (obj:`.Action.name`)."""
        return {a.name: a for a in self}

    @property
    def second_pass_result(self) -> ActionResult:
        """The single second pass result of that action indicated to invoke on the
        command line by the user.

        """
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
    controlling :class:`.Application`.  Method :meth:`_application_created`
    is invoked for each call back.

    .. document private functions
    .. automethod:: _application_created

    """
    @abstractmethod
    def _application_created(self, app: Application, action: Action):
        """Called just after the application target is created.

        :param app: the application that created the application target

        """
        pass


@dataclass
class Invokable(object):
    """A callable that invokes an :class:`.Action`.  This is used by
    :class:`.Application` to invoke the entire CLI application.

    """

    action: Action = field()
    """The action used to create this instance."""

    instance: Any = field()
    """The instantiated object generated from :obj:`action`."""

    method: Callable = field()
    """The object method bound to :obj:`instance` to be called."""

    args: Tuple[Any] = field()
    """The arguments used when calling :obj:`method`."""

    kwargs: Dict[str, Any] = field()
    """The keyword arguments used when calling :obj:`method`."""

    def __call__(self):
        """Call :obj:`method` with :obj:`args` and :obj:`kwargs`."""
        return self.method(*self.args, **self.kwargs)


@dataclass
class Application(Dictable):
    """An invokable application created using command line and application context
    data.  This class creates an instance of the *target application instance*,
    then invokes the corresponding action method.

    The application has all the first pass actions configured to run and/or
    given options indicating by the user to run (see
    :obj:`first_pass_actions`).  It also has the second pass action given as a
    mnemonic, or the single second pass action if there is only one (see
    :obj:`second_pas_action`).

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
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'setting CLI parameter {f.name} -> {val}')
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
                        f'No such option {name} parsed from CLI for ' +
                        f'method from {cmd_opts}: {meth_meta.name}')
                val: str = cmd_opts.get(name)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'meth map: {meth_meta.name}.{name} -> {val}')
                meth_params[name] = val
        if pos_arg_count != len(pos_args):
            raise ActionCliError(
                f'Method {meth_meta.name} expects {pos_arg_count} but got ' +
                f'{len(pos_args)} in {action.name}.{meth_meta.name}')
        return pos_args, meth_params

    def _pre_process(self, action: Action, instance: Any):
        if not action.cli.first_pass:
            config = self.config_factory.config
            cli_manager: ActionCliManager = self.factory.cli_manager
            if cli_manager.cleanups is not None:
                for sec in cli_manager.cleanups:
                    if sec not in config.sections:
                        raise ActionCliError(f'No section to remove: {sec}')
                    config.remove_section(sec)

    def _create_invokable(self, action: Action) -> Invokable:
        inst: Any = self._create_instance(action)
        self._pre_process(action, inst)
        meth_meta: ClassMethod = action.method_meta
        pos_args, meth_params = self._get_meth_params(action, meth_meta)
        meth = getattr(inst, meth_meta.name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'invoking {meth}')
        return Invokable(action, inst, meth, pos_args, meth_params)

    @property
    def first_pass_actions(self) -> Iterable[Action]:
        """All first pass actions registered in the application and/or indicated by the
        user to run via the command line.

        """
        return filter(lambda a: a.meta_data.first_pass, self.actions)

    @property
    def second_pass_action(self) -> Action:
        """The second pass action registered in the application and indicated to
        execute by the command line input.

        """
        acts = filter(lambda a: not a.meta_data.first_pass, self.actions)
        acts = tuple(acts)
        assert len(acts) == 1
        return acts[0]

    def _invoke_first_pass(self) -> Tuple[ActionResult]:
        """Invokes only the first pass actions and returns the results.

        """
        results: List[ActionResult] = []
        action: Action
        for action in self.first_pass_actions:
            invokable: Invokable = self._create_invokable(action)
            res: Any = invokable()
            results.append(ActionResult(action, invokable.instance, res))
        return tuple(results)

    def invoke_but_second_pass(self) -> Tuple[Tuple[ActionResult], Invokable]:
        """Invoke first pass actions but not the second pass action.

        :return: the results from the first pass actions and an invokable for
                 the second pass action

        """
        results: List[ActionResult] = list(self._invoke_first_pass())
        action: Action = self.second_pass_action
        invokable: Invokable = self._create_invokable(action)
        return results, invokable

    def invoke(self) -> ApplicationResult:
        """Invoke the application and return the results.

        """
        results, invokable = self.invoke_but_second_pass()
        res: Any = invokable()
        sp_res = ActionResult(invokable.action, invokable.instance, res)
        results.append(sp_res)
        return ApplicationResult(tuple(results))


@dataclass
class ApplicationFactory(PersistableContainer):
    """Boots the application context from the command line.  This first loads
    resource ``resources/app.conf`` from this package, then adds
    :obj:`app_config_resource` from the application package of the client.

    """
    package_resource: PackageResource = field()
    """Package resource (i.e. ``zensols.someappname``).  This field is converted to
    a package if given as a string during post initialization.

    """

    app_config_resource: Union[str, TextIOBase] = field(
        default='resources/app.conf')
    """The relative resource path to the application's context if :class:`str`.  If
    the type is an instance of :class:`io.TextIOBase`, then read it as a file
    object.

    """

    children_configs: Tuple[Configurable] = field(default=None)
    """Any children configurations added to the root level configuration."""

    reload_factory: bool = field(default=False)
    """If ``True``, reload classes in :class:`.ImportConfigFactory`.

    :see: :meth:`_create_config_factory`

    """

    reload_pattern: Union[re.Pattern, str] = field(default=None)
    """If set, reload classes that have a fully qualified name that match the
    regular expression regarless of the setting ``reload`` in
    :class:`.ImportConfigFactory`.

    :see: :meth:`_create_config_factory`

    """

    def __post_init__(self):
        if isinstance(self.package_resource, str):
            self.package_resource = PackageResource(self.package_resource)
        self._configure_serializer()
        self._resources = PersistedWork(
            '_resources', self, deallocate_recursive=True)

    def _configure_serializer(self):
        dist_name = self.package_resource.name
        Serializer.DEFAULT_RESOURCE_MODULE = dist_name

    def _create_application_context(self, app_context: Path) -> Configurable:
        """Factory method to create the application context from the :mod:`cli`
        resource (parent) context and a path to the application specific
        (child) context.

        :param parent_context: the :mod:`cli` root level context path

        :param app_context: the application child context path

        """
        children = []
        if self.children_configs is not None:
            children.extend(self.children_configs)
        return ImportIniConfig(app_context, children=children)

    def _create_config_factory(self, config: Configurable) -> ConfigFactory:
        """Factory method to create the configuration factory from the application
        context created in :meth:`_get_app_context`.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'reload: {self.reload_factory}')
        return ImportConfigFactory(config,
                                   reload=self.reload_factory,
                                   reload_pattern=self.reload_pattern)

    def _find_app_doc(self, cli_mng: ActionCliManager) -> str:
        """Try to find documentation suitable for the program as a fallback if the
        command line parser can't find anything.

        This returns the class level documentation if there is only one class
        by all second pass actions that don't originate from this module's
        parent (i.e. those, that come from :mod:`zensols.lib`).

        """
        def flt_act(action: ActionCli):
            name = action.class_meta.name
            return not action.first_pass and not name.startswith(mod_name)

        mod_name: str = DocUtil.module_name()
        ac_clis: Tuple[ActionCli] = tuple(cli_mng.actions.values())
        sp_actions = tuple(filter(flt_act, ac_clis))
        sp_metas = tuple(chain.from_iterable(
            map(lambda ac: ac.meta_datas, sp_actions)))
        doc = None
        if len(sp_metas) == 1:
            doc = sp_metas[0].doc
            doc = DocUtil.unnormalize(doc)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'using second pass doc: {doc}')
        else:
            actions: Dict[str, ActionCli] = \
                {c.class_meta.name: c for c in sp_actions}
            if len(actions) == 1:
                doc = next(iter(actions.values())).class_meta.doc.text
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'using class: {doc}')
        return doc

    def _get_app_doc(self, cli_mng: ActionCliManager) -> Optional[str]:
        """Return the application documentation, or ``None`` if it is unavailable.

        :see: :meth:`_find_app_doc`

        """
        doc = cli_mng.doc
        if doc is None:
            doc = self._find_app_doc(cli_mng)
        return doc

    def _get_config_path(self) -> Path:
        path: Path = self.package_resource.get_path(self.app_config_resource)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'path to app specific context: {path.absolute()}')
        if not path.exists():
            raise ActionCliError(
                f"Application context resource '{self.app_config_resource}' " +
                f'not found in {self.package_resource}')
        return path

    @persisted('_resources')
    def _create_resources(self) -> \
            Tuple[ConfigFactory, ActionCliManager, CommandLineParser]:
        """Create the config factory, the command action line manager, and command line
        parser resources.  The data is cached and use in property getters.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'create resources for: {type(self)}')
        if isinstance(self.app_config_resource, str):
            path = self._get_config_path()
            config: Configurable = self._create_application_context(path)
        else:
            file_obj = self.app_config_resource
            config: Configurable = self._create_application_context(file_obj)
        fac: ConfigFactory = self._create_config_factory(config)
        cli_mng: ActionCliManager = fac(ActionCliManager.SECTION)
        actions: Tuple[ActionMetaData] = tuple(chain.from_iterable(
            map(lambda a: a.meta_datas, cli_mng.actions.values())))
        config = CommandLineConfig(actions)
        parser = CommandLineParser(config, self.package_resource.version,
                                   default_action=cli_mng.default_action,
                                   application_doc=self._get_app_doc(cli_mng))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'created factory: {fac}')
        return fac, cli_mng, parser

    @property
    def config_factory(self) -> ConfigFactory:
        """The configuration factory used to create the application."""
        return self._create_resources()[0]

    @property
    def cli_manager(self) -> ActionCliManager:
        """The manager that creates the action based CLIs.

        """
        return self._create_resources()[1]

    @property
    def parser(self) -> CommandLineParser:
        """Used to parse the command line.

        """
        return self._create_resources()[2]

    def _parse(self, args: List[str]) -> Tuple[Action]:
        """Parse the command line.

        """
        fac, cli_mng, parser = self._create_resources()
        actions: List[Action] = []
        action_set: CommandActionSet = parser.parse(args)
        cmd_actions: Dict[str, CommandAction] = action_set.by_name
        action_cli: ActionCli
        for action_cli in cli_mng.actions_ordered:
            acli_meth: ActionCliMethod
            for acli_meth in action_cli.methods.values():
                name: str = acli_meth.action_meta_data.name
                caction: CommandAction = cmd_actions.get(name)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'action name: {name} -> {caction}')
                if caction is None and action_cli.always_invoke:
                    caction = CommandAction(acli_meth.action_meta_data, {}, ())
                if caction is not None:
                    action: Action = Action(
                        caction, action_cli,
                        acli_meth.action_meta_data, acli_meth.method)
                    actions.append(action)
        return actions

    def _get_default_args(self) -> List[str]:
        """Return the arguments to parse when none are given.  This defaults to the
        system arguments skipping the firt (program) argument.

        """
        return sys.argv[1:]

    def create(self, args: List[str] = None) -> Application:
        """Create the action CLI application.

        :param args: the arguments to the application; if this is a string, it
                     will be converted to a list by splitting on whitespace;
                     this defaults to the output of :meth:`_get_default_args`

        :raises ActionCliError: for any missing data or misconfigurations

        """
        # we have to clear previously created resources for multiple calls to
        # this method for this instance
        self._resources.clear()
        fac, cli_mng, parser = self._create_resources()
        if args is None:
            args = self._get_default_args()
        actions: Tuple[Action] = self._parse(args)
        return Application(fac, self, actions)

    def _error_to_str(self, ex: Exception) -> str:
        """Create a command line friendly error message fromt he exception."""
        s = str(ex)
        s = s[0].lower() + s[1:]
        return s

    def _handle_error(self, ex: Exception):
        """Handle errors raised during the execution of the application.

        :see: :meth:`invoke`

        """
        if isinstance(ex, ConfigurableFileNotFoundError):
            # in some cases, the parser can not be created because it needs
            # configuration that can not be loaded
            prog = Path(sys.argv[0]).name
            msg = self._error_to_str(ex)
            print(f'{prog}: error: {msg}', file=sys.stderr)
        elif isinstance(ex, ActionCliError):
            msg = self._error_to_str(ex)
            self.parser.error(msg)
        else:
            raise ex

    def invoke(self, args: Union[List[str], str] = None) -> Any:
        """Creates and invokes the entire application returning the result of the
        second pass action.

        ;param args: the arguments to the application; if this is a string, it
                     will be converted to a list by splitting on whitespace;
                     this defaults to the output of :meth:`_get_default_args`

        :raises ActionCliError: for any missing data or misconfigurations

        :return: the result of the second pass action

        """
        if isinstance(args, str):
            args = args.split()
        try:
            app: Application = self.create(args)
            app_res: ApplicationResult = app.invoke()
            act_res: ActionResult = app_res()
            return act_res
        except Exception as e:
            self._handle_error(e)

    def invoke_protect(self, args: Union[List[str], str] = None) -> Any:
        """Same as :meth:`invoke`, but protect against :class:`Exception` and
        :class:`SystemExit`.  If an error is raised while invoking, it is
        logged and returned.

        ;param args: the arguments to the application; if this is a string, it
                     will be converted to a list by splitting on whitespace;
                     this defaults to the output of :meth:`_get_default_args`

        :return: the result of the second pass action or the output of
                 :func:`sys.exec_info`

        """
        try:
            return self.invoke(args)
        except (Exception, SystemExit) as e:
            exc_info = sys.exc_info()
            logger.error(f'invocation failed: {e}', exc_info=exc_info)
            return exc_info
