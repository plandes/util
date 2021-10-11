"""First pass application to export the environment

"""
__author__ = 'Paul Landes'

from typing import Dict, Type, Any
from dataclasses import dataclass, field
from enum import Enum, auto, EnumMeta
import sys
import logging
import inspect
from json import JSONEncoder
from io import TextIOBase
from pathlib import Path
from zensols.config import Configurable, Dictable, ConfigFactory
from zensols.introspect import ClassImporter
from .. import (
    Action, ActionCli, ActionCliMethod, ActionMetaData,
    Application, ApplicationObserver,
)

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """The format for the environment export with the :class:`.ExportEnvironment`
    first pass application.

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


@dataclass
class ExportEnvironment(object):
    """The class dumps a list of bash shell export statements for sourcing in build
    shell scripts.

    """
    # we can't use "output_format" because ListActions would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'export_output_format'
    OUTPUT_PATH = 'output_path'
    CLI_META = {'option_includes': {OUTPUT_FORMAT, OUTPUT_PATH},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'expfmt',
                                 'short_name': None},
                 OUTPUT_PATH: {'long_name': 'expout',
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
                meth: ActionCliMethod
                for name, meth in action_cli.methods.items():
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
                print(self.asjson(indent=4, cls=ActionEncoder))
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
    """The class dumps a list of bash shell export statements for sourcing in build
    shell scripts.

    """
    # we can't use "output_format" because ListActions would use the same
    # causing a name collision
    OUTPUT_FORMAT = 'config_output_format'
    OUTPUT_PATH = 'config_output_path'
    CLI_META = {'mnemonic_overrides': {'show_config': 'config'},
                'option_includes': {OUTPUT_FORMAT, OUTPUT_PATH},
                'option_overrides':
                {OUTPUT_FORMAT: {'long_name': 'cnffmt',
                                 'short_name': None},
                 OUTPUT_PATH: {'long_name': 'cnfout',
                               'short_name': None}}}

    config: Configurable = field()
    """The output format of the configuration."""

    config_factory: ConfigFactory = field()
    """The configuration factory which is returned from the app."""

    config_output_path: Path = field(default=None)
    """The output file name for the configuration."""

    config_output_format: ConfigFormat = field(default=ConfigFormat.text)
    """The output format."""

    def show_config(self) -> Configurable:
        """Print the configuration and exit."""
        fmt = self.config_output_format
        if self.config_output_path is None:
            writer = sys.stdout
        else:
            writer = open(self.config_output_path, 'w')
        try:
            if fmt == ConfigFormat.text:
                self.config.write(writer=writer)
            elif fmt == ConfigFormat.ini:
                print(self.config.get_raw_str().rstrip(), file=writer)
            elif fmt == ConfigFormat.json:
                print(self.config.asjson(indent=4), file=writer)
        finally:
            if self.config_output_path is not None:
                writer.close()
        return self.config_factory

    def __call__(self):
        return self.show_config()
