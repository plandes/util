"""General purpose first pass applications to support the build and
configuration functionality.

"""
__author__ = 'Paul Landes'

from typing import Dict, Type, Any, Optional, Tuple, List, Union
from dataclasses import dataclass, field
from enum import Enum, auto, EnumMeta
import sys
import os
import re
import logging
import inspect
from json import JSONEncoder
from io import TextIOBase
from pathlib import Path
import shutil
from zensols.config import (
    Configurable, Dictable, ConfigFactory, DictionaryConfig
)
from zensols.introspect import ClassImporter
from .. import (
    Action, ActionCli, ActionCliError, ActionCliMethod, ActionMetaData,
    ActionCliManager, Application, ApplicationObserver,
)
from .. import ConfigurationImporter
from zensols.config.importfac import _AliasImportConfigFactoryModule

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """The format for the environment export with the
    :class:`.ExportEnvironment` first pass application.

    """
    bash = auto()
    make = auto()


class ListFormat(Enum):
    """Options for outputing the action list in :class:`.ListActions`.

    """
    text = auto()
    json = auto()
    name = auto()


class ConfigFormat(Enum):
    """Options for outputing the action list in :class:`.ShowConfiguration`.

    """
    text = auto()
    ini = auto()
    json = auto()
    yaml = auto()
    shell = auto()


@dataclass
class DryRunApplication(object):
    CLI_META = {'option_overrides': {'dry_run': {'short_name': 'd'}}}

    dry_run: bool = field(default=False)
    """Don't do anything; just act like it."""


@dataclass
class ExportEnvironment(object):
    """The class dumps a list of bash shell export statements for sourcing in
    build shell scripts.

    """
    # we can't use "output_format" because ListActions would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'export_output_format'
    OUTPUT_PATH = 'output_path'
    CLI_META = {'option_includes': {OUTPUT_FORMAT, OUTPUT_PATH},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'eformat',
                                 'short_name': None},
                 OUTPUT_PATH: {'long_name': 'eout',
                               'short_name': None}}}

    config: Configurable = field()
    """The configuration used to get section information used to generate the
    export commands.

    """
    section: str = field()
    """The section to dump as a series of export statements."""

    output_path: Path = field(default=None)
    """The output file name for the export script."""

    export_output_format: ExportFormat = field(default=ExportFormat.bash)
    """The output format."""

    def _write(self, writer: TextIOBase):
        exports: Dict[str, str] = self.config.populate(section=self.section)
        if self.export_output_format == ExportFormat.bash:
            fmt = 'export {k}="{v}"\n'
        else:
            fmt = '{k}={v}\n'
        for k, v in exports.asdict().items():
            writer.write(fmt.format(**{'k': k.upper(), 'v': v}))

    def export(self) -> Path:
        """Create exports for shell sourcing."""
        if self.output_path is None:
            self._write(sys.stdout)
        else:
            with open(self.output_path, 'w') as f:
                self._write(f)
        return self.output_path

    def __call__(self) -> Path:
        return self.export()


@dataclass
class ListActions(ApplicationObserver, Dictable):
    """List command line actions with their help information.

    """
    LONG_NAME_SKIP = 'add_ConfigFactoryAccessor_to_app_config'
    """The :class:`.ActionCliMethod` name to skip,which indicates the first pass
    action used to get the application in the :class:`.CliHarness` used by
    :class:`.ConfigFactoryAccessor`.

    """
    # we can't use "output_format" because ExportEnvironment would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'list_output_format'
    CLI_META = {'option_includes': {OUTPUT_FORMAT},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'lstfmt',
                                 'short_name': None}}}

    list_output_format: ListFormat = field(default=ListFormat.text)
    """The output format for the action listing."""

    type_to_string: Dict[Type, str] = field(
        default_factory=lambda: {Path: 'path'})
    """Map Python type to a string used in the JSON formatted list output."""

    def __post_init__(self):
        self._command_line = False

    def _application_created(self, app: Application, action: Action):
        """In this call back, set the app and action for using in the invocation
        :meth:`add`.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def _from_dictable(self, *args, **kwargs) -> Dict[str, Any]:
        action_cli: ActionCli
        ac_docs: Dict[str, str] = {}
        for action_cli in self._app.factory.cli_manager.actions_ordered:
            if not action_cli.first_pass:
                name: str
                meth: ActionCliMethod
                for name, meth in action_cli.methods.items():
                    if name == self.LONG_NAME_SKIP:
                        continue
                    meta: ActionMetaData = meth.action_meta_data
                    if self._command_line:
                        md = meta.asdict()
                        del md['first_pass']
                        ac_docs[name] = md
                    else:
                        ac_docs[name] = meta.doc
        return ac_docs

    def list(self):
        """List all actions and help."""
        class ActionEncoder(JSONEncoder):
            def default(self, obj: Any) -> str:
                if isinstance(obj, EnumMeta) or inspect.isclass(obj):
                    val = tm.get(obj)
                    if val is None:
                        val = ClassImporter.full_classname(obj)
                    return val
                return JSONEncoder.default(self, obj)

        tm = self.type_to_string

        def list_json():
            try:
                self._command_line = True
                print(self.asjson(flatten=False, indent=4, cls=ActionEncoder))
            finally:
                self._command_line = False

        return {
            ListFormat.name: lambda: print('\n'.join(self.asdict().keys())),
            ListFormat.text: lambda: self.write(),
            ListFormat.json: list_json,
        }[self.list_output_format]()

    def __call__(self):
        return self.list()


@dataclass
class ShowConfiguration(object):
    """The class dumps a list of bash shell export statements for sourcing in
    build shell scripts.

    """
    # we can't use "output_format" because ListActions would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'config_output_format'
    OUTPUT_PATH = 'config_output_path'
    SECTION_NAME = 'sections'
    EVAL_NAME = 'evaluate'
    CLI_META = {'mnemonic_overrides': {'show_config': 'config'},
                'option_includes':
                {OUTPUT_FORMAT, OUTPUT_PATH, SECTION_NAME, EVAL_NAME},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'cformat', 'short_name': None},
                 OUTPUT_PATH: {'long_name': 'cout', 'short_name': None},
                 SECTION_NAME: {'long_name': 'csec', 'short_name': None},
                 EVAL_NAME: {'long_name': 'eval', 'short_name': None}}}

    config_factory: ConfigFactory = field()
    """The configuration factory which is returned from the app."""

    config_output_path: Path = field(default=None)
    """The output file name for the configuration."""

    config_output_format: ConfigFormat = field(default=ConfigFormat.text)
    """The output format."""

    evaluate: bool = field(default=False)
    """Whether to evaluate as the application sees it."""

    def _eval_config(self, config: Configurable) -> Configurable:
        secs: Dict[str, Dict[str, str]] = {}
        sec_name: str
        for sec_name in config.sections:
            sec: Dict[str, str] = dict(map(
                lambda t: (t[0], str(t[1])),
                config.populate({}, sec_name).items()))
            secs[sec_name] = sec
        return DictionaryConfig(secs)

    def _write_config(self, writer: TextIOBase, fmt: ConfigFormat,
                      sections: str):
        def pr(s: str):
            writer.write(s)
            writer.write('\n')

        def prshell():
            i: int
            sec: str
            for i, sec in enumerate(conf.sections):
                if i > 0:
                    writer.write('\n')
                writer.write(f'# {sec}\n')
                for k, v in conf.get_options(sec).items():
                    writer.write(f'{k.upper()}="{v}"\n')

        conf: Configurable = self.config_factory.config
        if sections is not None:
            dconf = DictionaryConfig()
            conf.copy_sections(dconf, re.split(r'\s*,\s*', sections))
            conf = dconf
        if self.evaluate:
            conf = self._eval_config(conf)
        {
            ConfigFormat.text: lambda: conf.write(writer=writer),
            ConfigFormat.ini: lambda: pr(conf.get_raw_str().rstrip()),
            ConfigFormat.json: lambda: pr(conf.asjson(indent=4)),
            ConfigFormat.yaml: lambda: pr(conf.asyaml(indent=4)),
            ConfigFormat.shell: prshell,
        }[fmt]()

    def show_config(self, sections: str = None) -> Configurable:
        """Print the configuration and exit.

        :param sections: comma separated sections to show, all if not given, or
                         - for names

        """
        fmt = self.config_output_format
        if self.config_output_path is None:
            writer = sys.stdout
        else:
            writer = open(self.config_output_path, 'w')
        try:
            if sections == '-':
                secs = '\n'.join(sorted(self.config_factory.config.sections))
                writer.write(secs + '\n')
            else:
                self._write_config(writer, fmt, sections)
        finally:
            if self.config_output_path is not None:
                writer.close()
        return self.config_factory

    def __call__(self):
        return self.show_config()


@dataclass
class EditConfiguration(object):
    """Edits the configuration file given on the command line.  This must be
    added *after* the :class:`~zensols.cli.ConfigurationImporter` class.

    """
    CLI_META = {'option_includes': set(),
                'mnemonic_overrides': {'edit_configuration': 'editconf'}}

    config_factory: ConfigFactory = field()
    """The configuration factory which is returned from the app."""

    section_name: str = field(default='config_cli')
    """The section of the CLI configuration that contains the entry."""

    command: str = field(default='emacsclient -n {path}')
    """The command used on the :function:`os.system` command to edit the file.

    """
    def edit_configuration(self):
        """Edit the configuration file."""
        sec = self.config_factory(self.section_name)
        attr: str = ConfigurationImporter.CONFIG_PATH_FIELD
        path: Path = getattr(sec, attr)
        path = str(path.absolute())
        cmd = self.command.format(**dict(path=path))
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'editing file: {path}')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'system: {cmd}')
        os.system(cmd)


@dataclass
class ProgramNameConfigurator(object):
    """Adds a section with the name of the program to use.  This is useful for
    adding the program name to the beginning of logging lines to confirm to
    UNIX conventions.

    To add it to the logging output add it to the
    :class:`~zensols.cli.LogConfigurator` section's ``format`` property.

    Example::

        [add_prog_cli]
        class_name = zensols.cli.ProgramNameConfigurator
        default = someprog

        [log_cli]
        class_name = zensols.cli.LogConfigurator
        format = ${program:name}: %%(message)s

    """
    CLI_META = {'first_pass': True,  # not a separate action
                # since there are no options and this is a first pass, force
                # the CLI API to invoke it as otherwise there's no indication
                # to the CLI that it needs to be called
                'always_invoke': True,
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'mnemonic_includes': {'add_program_name'},
                'option_includes': {}}

    config: Configurable = field()
    """The parent configuration, which is populated with the package
    information.

    """
    section: str = field(default='program')
    """The name of the section to create with the package information."""

    default: str = field(default='prog')
    """The default progran name to use when can not be inferred."""

    @classmethod
    def infer_program_name(self, entry_path: str = None) -> Optional[str]:
        """Infer the program name using the system arguments.

        :param entry_path: used to infer the program name from the entry point
                           script, which defaults ``sys.argv[0]``

        """
        entry_path = sys.argv[0] if entry_path is None else entry_path
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'command line leading arg: <{entry_path}>')
        if entry_path is not None and len(entry_path) > 0:
            return Path(entry_path).stem

    def create_section(self, entry_path: str = None) -> Dict[str, str]:
        """Return a dict with the contents of the program and name section.

        :param entry_path: used to infer the program name from the entry point
                           script, which defaults ``sys.argv[0]``

        """
        prog_name = self.infer_program_name(entry_path) or self.default
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'using program name: {prog_name}')
        return {self.section: {'name': prog_name}}

    def add_program_name(self):
        """Add the program name as a single configuration section and parameter.

        :see: :obj:`section`

        :see: :obj:`default`
        """
        d_conf = DictionaryConfig(self.create_section())
        d_conf.copy_sections(self.config)


@dataclass
class Cleaner(DryRunApplication):
    """Clean (removes) files and directories not needed by the project.  The
    first tuple of paths will get deleted at any level, the next needs a level
    of 1 and so on.

    """
    CLASS_INSPECTOR = {}
    CLI_META = ActionCliManager.combine_meta(
        DryRunApplication,
        {'mnemonic_includes': {'clean'},
         'option_excludes': {'paths'},
         'option_overrides': {'clean_level': {'long_name': 'clevel',
                                              'short_name': None}}})

    paths: Tuple[Tuple[Union[str, Path], ...], ...] = field(default=None)
    """Paths to delete (files or directories) with each group corresponding to a
    level (see class docs).

    """
    clean_level: int = field(default=0)
    """The level at which to delete."""

    def __post_init__(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'cleaner: created with paths: {self.paths}')

    def _remove_path(self, level: int, glob: Path) -> bool:
        if logger.isEnabledFor(logging.WARNING):
            logger.warn(f'cleaning at level {level} using {glob}')
        if glob.parent.name == '**':
            parent = glob.parent.parent
            pat = f'{glob.parent}/{glob.name}'
        else:
            parent = glob.parent
            pat = glob.name
        for path in parent.glob(pat):
            if path.exists():
                if logger.isEnabledFor(logging.WARNING):
                    logger.warn(f'removing (level {level}): {path}')
                if not self.dry_run:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()

    def clean(self):
        """Clean up unecessary files."""
        if logger.isEnabledFor(logging.WARNING):
            logger.warn(f'cleaning at max level {self.clean_level}')
        for level, paths in enumerate(self.paths):
            if level <= self.clean_level:
                for path in paths:
                    if isinstance(path, str):
                        path = Path(path).expanduser()
                    self._remove_path(level, path)

    def __call__(self):
        self.clean()


@dataclass
class CacheClearer(DryRunApplication):
    """Clear cached data by iterating through a list of application context
    instances that have a ``clear`` method.

    """
    CLASS_INSPECTOR = {}
    CLI_META = ActionCliManager.combine_meta(
        DryRunApplication,
        {'mnemonic_includes': {'clear'},
         'option_excludes': {'config_factory', 'clearables'},
         'option_overrides': {'clean_level': {'long_name': 'clevel',
                                              'short_name': None}}})

    config_factory: ConfigFactory = field(default=None)
    """The parent application context factory, which is populated from the child
    configuration (see class docs).

    """
    clearables: Tuple[str, ...] = field(default=None)
    """A list of instance aliases (``<section>:<option>``), each with their own
    list of instances to invoke ``clear`` to remove cached data.

    """
    def clear(self):
        """Clear *all* cached data"""
        config: Configurable = self.config_factory.config
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'clearing: {self.clearables}')
        clearable: str
        for clearable in self.clearables:
            sec: str
            option: str
            sec, option = _AliasImportConfigFactoryModule.parse(clearable)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'clearing section: {sec}, option: {option}')
            if sec not in config.sections:
                raise ActionCliError(f'Missing section to clear: {sec}')
            inst_names: List[str] = config.get_option_list(option, sec)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'clearing instances: {inst_names}')
            inst_name: str
            for inst_name in inst_names:
                inst: Any = self.config_factory(inst_name)
                if logger.isEnabledFor(logging.INFO):
                    nm = inst.name if hasattr(inst, 'name') else str(type(inst))
                    logger.info(f'clearing instance: {nm}')
                if not hasattr(inst, 'clear'):
                    raise ActionCliError(
                        f"No clear method on '{inst_name}' ({type(inst)})")
                if not self.dry_run:
                    inst.clear()
