from __future__ import annotations
"""A more object oriented data driven command line set of classes.

"""

from typing import Tuple, List, Dict, Iterable, Any
from dataclasses import dataclass, field
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
    WRITABLE__DESCENDANTS = True

    command_action: CommandAction = field()
    """The result of the command line parsing of the action.  It contains the data
    parsed on a per action level.

    """

    action_cli: ActionCli = field()
    """Command line interface of the action meta data."""

    action_meta_data: ActionMetaData = field()
    """An action represents a link between a command line mnemonic *action* and a
    method on a class to invoke.

    """

    method_meta: ClassMethod = field()
    """The metadata of the method to use for the invocation of the action.

    """

    @property
    def section(self) -> str:
        return self.action_cli.section

    @property
    def class_meta(self) -> Class:
        return self.action_cli.class_meta

    @property
    def method_name(self) -> str:
        return self.method_meta.name

    @property
    def class_name(self) -> str:
        return self.class_meta.name

    def _get_dictable_attributes(self) -> Iterable[Tuple[str, str]]:
        return map(lambda f: (f, f),
                   'section class_name method_name command_action'.split())


@dataclass
class ApplicationResult(Dictable):
    instance: Any
    result: Any


@dataclass
class Application(Dictable):
    """An invokable application created using command line and application context
    data.

    """
    WRITABLE__DESCENDANTS = True

    config_factory: ConfigFactory = field(repr=False)
    """The factory used to create the application and its components."""

    actions: Tuple[Action] = field()
    """The list of actions to invoke in order."""

    def _create_instance(self, action: Action) -> Any:
        cmd_opts: Dict[str, Any] = action.command_action.options
        field: ClassField
        const_params: Dict[str, Any] = {}
        sec = action.section
        for f in action.class_meta.fields.values():
            val: str = cmd_opts.get(f.name)
            if val is None:
                continue
            # if val is None:
            #     raise ActionCliError(
            #         f'field not found for section {action.section} ' +
            #         f'({action.class_name}): {f.name}')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'field map: {sec}:{f.name} -> {val}')
            const_params[f.name] = val
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating {sec} with {const_params}')
        inst = self.config_factory.instance(sec, **const_params)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'created instance of type {type(inst)}')
        return inst

    def _get_meth_params(self, action: Action, meth_meta: ClassMethod) -> \
            Tuple[Tuple[Any], Dict[str, Any]]:
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
                val: str = cmd_opts[name]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'meth map: {name} -> {val}')
                meth_params[name] = val
        if pos_arg_count != len(pos_args):
            raise ActionCliError(f'method {meth_meta.name} expects ' +
                                 f'{pos_arg_count} but got {len(pos_args)}')
        return pos_args, meth_params

    def invoke(self) -> Tuple[ApplicationResult]:
        results: List[ApplicationResult] = []
        action: Action
        for action in self.actions:
            inst = self._create_instance(action)
            meth_meta: ClassMethod = action.method_meta
            pos_args, meth_params = self._get_meth_params(action, meth_meta)
            meth = getattr(inst, meth_meta.name)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'invoking {meth} on {type(inst)}')
            res: Any = meth(*pos_args, **meth_params)
            results.append(ApplicationResult(inst, res))
        return tuple(results)


@dataclass
class ApplicationFactory(object):
    """Boots the application context from the command line.

    """
    UTIL_PACKAGE = 'zensols.util'
    """The package name of *this* utility package."""

    package_resource: PackageResource = field()
    """Package resource (i.e. zensols.someappname)."""

    app_config_resource: str = field(default='resources/app.conf')
    """The relative resource path to the application's context."""

    @classmethod
    def instance(cls, package_name: str,
                 *args, **kwargs) -> ApplicationFactory:
        """"A create facade method.

        :param package_name: used to create the :obj:`package_resource`

        :param app_config_resource: see class docs

        """
        pres = PackageResource(package_name)
        return cls(pres, *args, **kwargs)

    def _get_app_context(self, app_context: Path) -> Configurable:
        pres = PackageResource(self.UTIL_PACKAGE)
        res = self.app_config_resource
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'looking up resource: {res} in {pres}')
        path = pres.get_path(res)
        if not path.exists():
            # this should never not happen
            raise ValueError(f'no application context found: {path}')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'loading app config: {path}')
        app_conf = DictionaryConfig(
            {'import_app': {'config_file': str(app_context.absolute()),
                            'type': 'ini'}})
        return ImportIniConfig(path, children=(app_conf,))

    @persisted('_resources')
    def _create_resources(self) -> \
            Tuple[ConfigFactory, ActionCliManager, CommandLineParser]:
        path = self.package_resource.get_path(self.app_config_resource)
        if not path.exists():
            raise ActionCliError(
                f"application context resource '{self.app_config_resource}' " +
                f'not found in {self.package_resource}')
        config = self._get_app_context(path)
        fac = ImportConfigFactory(config)
        cli_mng: ActionCliManager = fac(ActionCliManager.SECTION)
        actions: Tuple[ActionMetaData] = tuple(chain.from_iterable(
            map(lambda a: a.meta_datas, cli_mng.actions.values())))
        config = CommandLineConfig(actions)
        parser = CommandLineParser(config, self.package_resource.version)
        return fac, cli_mng, parser

    @property
    def parser(self) -> CommandLineParser:
        return self._create_resources()[2]

    @property
    def cli_manager(self) -> ActionCliManager:
        return self._create_resources()[1]

    def _parse(self, args: List[str]) -> Tuple[Action]:
        fac, cli_mng, parser = self._create_resources()
        actions: List[Action] = []
        action_set: CommandActionSet = parser.parse(args)
        action_clis: Dict[str, ActionCli] = cli_mng.actions_by_meta_data_name
        caction: CommandAction
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
        return Application(fac, actions)
