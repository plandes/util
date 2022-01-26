"""Configuration merging first pass applications.  These utility applications
allow a configuration option and then merge that configuration with the
application context.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Set, List
from dataclasses import dataclass, field
import os
import logging
from string import Template
import re
from pathlib import Path
from zensols.util import PackageResource
from zensols.config import (
    rawconfig, Configurable, ConfigurableFactory,
    IniConfig, ImportIniConfig, StringConfig, DictionaryConfig,
)
from .. import (
    ActionCliError, ApplicationError, OptionMetaData, ActionMetaData,
    ApplicationObserver, Action, Application,
)

logger = logging.getLogger(__name__)


class ConfiguratorImporterTemplate(Template):
    delimiter = '^'


@dataclass
class ConfigurationImporter(ApplicationObserver):
    """This class imports a child configuration in to the application context.  It
    does this by:

      1. Attempt to load the configuration indicated by the ``--config``
         option.

      2. If the option doesn't exist, attempt to get the path to load from an
         environment variable (see :meth:`get_environ_var_from_app`).

      3. Loads the *child* configuration.

      4. Copy all sections from the child configuration to :obj:`config`.

    The child configuration is created by :class:`.ConfigurableFactory`.  If
    the child has a `.conf` extension, :class:`.ImportIniConfig` is used with
    its child set as :obj:`config` so the two can reference each other at
    property/factory resolve time.

    In the case the child configuration is loaded

    """
    CONFIG_PATH_FIELD = 'config_path'
    """The field name in this class of the child configuration path."""

    CLI_META = {'first_pass': True,  # not a separate action
                # the mnemonic must be unique and used to referece the method
                'mnemonic_overrides': {'merge': '_merge_config_as_import'},
                'mnemonic_includes': {'merge'},
                # better/shorter  long name, and reserve the short name
                'option_overrides': {CONFIG_PATH_FIELD: {'long_name': 'config',
                                                         'short_name': 'c'}},
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'option_includes': {CONFIG_PATH_FIELD}}
    """Command line meta data to avoid having to decorate this class in the
    configuration.  Given the complexity of this class, this configuration only
    exposes the parts of this class necessary for the CLI.

    """

    IMPORT_TYPE = 'import'
    """The string value of the ``type`` parameter in the section config identifying
    an :class:`.ImportIniConfig` import section.

    """

    ENVIRON_VAR_REGEX = re.compile(r'^.+\.([a-z]+?)$')
    """A regular expression to parse the name from the package name for the
    environment variable that might hold the configuration
    (i.e. ``APPNAMERC``).

    """
    name: str = field()
    """The section name."""

    config: Configurable = field()
    """The parent configuration, which is populated from the child configuration
    (see class docs).

    """

    expect: bool = field(default=True)
    """If ``True``, raise an :class:`.ApplicationError` if the option is not given.

    """

    default: Path = field(default=None)
    """Use this file as the default when given on the command line, which is not
    used unless :obj:``expect`` is set to ``False``.

    If this is set to ``skip``, then do not load any file.  This is useful when
    the entire configuration is loaded by this class and there are
    configuration mentions in the ``app.conf`` application context.

    """

    config_path_environ_name: str = field(default=None)
    """An environment variable containing the default path to the configuration.

    """

    type: str = field(default=None)
    """The type of :class:`.Configurable` use to create in
    :class:`.ConfigurableFactory`.  If this is not provided, the factory
    decides based on the file extension.

    :see: :class:`.ConfigurableFactory`

    """

    arguments: Dict[str, Any] = field(default=None)
    """Additional arguments to pass to the :class:`.ConfigFactory` when created.

    """

    section: str = field(default=None)
    """Additional which section to load as an import.  This is only valid and used
    when :obj:`type` is set to `import`.  When it is, the section will replace
    the string ``^{config_apth}`` (and any other field in this instance using
    the same syntax) and load indicated remaining configuration using
    :class:`~zensols.config.ImportIniConfig`.

    See the `API documentation
    <https://plandes.github.io/util/doc/config.html#import-ini-configuration>`_
    for more information.

    """

    config_path_option_name: str = field(default='config_path')
    """If not ``None``, the name of the option to set in the section defined for
    this instance (section = :obj:`name`).

    """

    debug: bool = field(default=False)
    """Printn the configuration after the merge operation."""

    # name of this field must match :obj:`ConfigurationImporter.CONFIG_PATH_FIELD`
    config_path: Path = field(default=None)
    """The path to the configuration file."""

    def get_environ_var_from_app(self) -> str:
        """Return the environment variable based on the name of the application.  This
        returns the :obj:`config_path_environ_name` if set, otherwise, it
        generates it based on the name returned from the packge + ``RC`` and
        capitalizes it.

        """
        if self.config_path_environ_name is not None:
            name = self.config_path_environ_name
        else:
            pkg_res: PackageResource = self._app.factory.package_resource
            name: str = pkg_res.name
            m = self.ENVIRON_VAR_REGEX.match(name)
            if m is not None:
                name = m.group(1)
            name = f'{name}rc'.upper()
        return name

    def _get_config_option(self) -> str:
        """Return the long option name (with dashes) as given on the command line.

        """
        ameta: ActionMetaData = self._action.meta_data
        ometa: OptionMetaData = ameta.options_by_dest[self.CONFIG_PATH_FIELD]
        return ometa.long_option

    def _application_created(self, app: Application, action: Action):
        """In this call back, set the app and action for using in the invocation
        :meth:`merge`.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configurator created with {action}')
        self._app = app
        self._action = action

    def _validate(self):
        # the section attribute is only useful for ImportIniConfig imports
        if self.type != self.IMPORT_TYPE and self.section is not None:
            raise ActionCliError("Cannot have a 'section' entry " +
                                 f"without type of '{self.IMPORT_TYPE}'")

    def _populate_import_sections(self, config: Configurable) -> Configurable:
        sec: Dict[str, str] = self.config.get_options(self.section)
        secs = {}
        populated_sec = {}
        vals = self.__dict__
        for k, v in sec.items():
            populated_sec[k] = v.format(**vals)
        secs[ImportIniConfig.IMPORT_SECTION] = populated_sec
        if ImportIniConfig.SECTIONS_SECTION in populated_sec:
            sub_secs: List[str] = self.config.serializer.parse_object(
                self.config.get_option(
                    ImportIniConfig.SECTIONS_SECTION, self.section))
            for sec in sub_secs:
                repl_sec = {}
                secs[sec] = repl_sec
                with rawconfig(config):
                    for k, v in config.get_options(sec).items():
                        tpl = ConfiguratorImporterTemplate(v)
                        vr = tpl.substitute(vals)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'{sec}:{k}: {v} -> {vr}')
                        repl_sec[k] = vr
        return DictionaryConfig(secs)

    def _load_configuration(self) -> Configurable:
        """Once we have the path and the class used to load the configuration, create
        the instance and load it.

        Special handling is required to make options forward *and* backward
        propogate.

        """
        if logger.isEnabledFor(logging.INFO):
            logger.info('configurator loading section: ' +
                        f'{self.config.config_file}:[{self.name}]')

        # the modified configuration that will returned
        modified_config: Configurable = self.config
        # sections created during this call to later be removed
        secs_to_del: Set[str] = set()
        # create the command line specified config
        do_back_copy: bool = True
        # config section sanity check
        self._validate()
        # create a configuration factory using the configuration file extension
        if self.type is None:
            args = {} if self.arguments is None else self.arguments
            cf = ConfigurableFactory(kwargs=args)
            if self.config_path is None:
                # this happens when expect=False and no configuration is given
                cl_config = DictionaryConfig()
            else:
                cl_config = cf.from_path(self.config_path)
                logger.info(f'config loaded {self.config_path} as ' +
                            f'type {cl_config.__class__.__name__}')
        # import using ImportIniConfig as a section
        elif self.type == self.IMPORT_TYPE:
            args: dict = {} if self.arguments is None else self.arguments
            ini: IniConfig = IniConfig(self.config)
            dconf: Configurable = self._populate_import_sections(ini)
            secs_to_del.update(dconf.sections)
            dconf.copy_sections(ini)
            with rawconfig(ini):
                cl_config = ImportIniConfig(
                    config_file=ini,
                    children=self._app.factory.children_configs,
                    **args)
            with rawconfig(cl_config):
                cl_config.copy_sections(self.config)
            modified_config = cl_config
            # remove sections that were removed
            removed_secs: Set[str] = self.config.sections - cl_config.sections
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'removing additional sections: {removed_secs}')
            secs_to_del.update(removed_secs)
            # avoid the two way copy that happens later
            do_back_copy = False
        # otherwise, use the type to tell the configuraiton factory how to
        # create it
        else:
            args = {'config_file': self.config_path}
            if self.arguments is not None:
                args.update(self.arguments)
            cf = ConfigurableFactory(kwargs=args)
            cl_config = cf.from_type(self.type)
            logger.info(f'configurator loading {self.config_path} from ' +
                        f'type {self.type}')

        # For non-import configs, first inject our app context (app.conf) to
        # the command line specified configuration (--config) skipping sections
        # that have missing options.  Examples of those missing include
        # cyclical dependencies such option references from our app context to
        # the command line context.
        if do_back_copy:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'copying app config to {cl_config}')
            with rawconfig(self.config):
                self.config.copy_sections(cl_config)

        # copy the command line config to our app context letting it barf with
        # any missing properties this time
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'copying to app config: {cl_config}')
        if do_back_copy:
            with rawconfig(cl_config):
                cl_config.copy_sections(self.config)
        # if we imported, we created ImportIniConfig sections we need to remove
        for sec in secs_to_del:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'removing (added) section: {sec}')
            self.config.remove_section(sec)
        if self.debug:
            print(self.config.get_raw_str())
        return modified_config

    def _load(self) -> Configurable:
        """Load the configuration and update the application context.

        """
        modified_config = self._load_configuration()
        if self.config_path_option_name is not None:
            self.config.set_option(
                self.config_path_option_name,
                f'path: {str(self.config_path)}',
                section=self.name)
        return modified_config

    def _reset(self):
        """Reset the Python logger configuration."""
        root = logging.getLogger()
        tuple(map(root.removeHandler, root.handlers[:]))
        tuple(map(root.removeFilter, root.filters[:]))

    def merge(self) -> Configurable:
        """Merge configuration at path to the current configuration.

        :param config_path: the path to the configuration file

        """
        # the modified configuration that will returned
        modified_config: Configurable = self.config
        env_var: str = None
        rc_path: Path = None
        if self.config_path is None:
            env_var: str = self.get_environ_var_from_app()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"loading config from env var '{env_var}'")
            env_var_path: str = os.environ.get(env_var)
            if env_var_path is not None:
                rc_path = Path(env_var_path)
                if rc_path.exists():
                    self.config_path = rc_path
            elif self.default is not None:
                if self.default == 'skip':
                    self.config_path = None
                else:
                    self.config_path = self.default
        if self.config_path is None:
            if self.expect:
                lopt = self._get_config_option()
                if env_var is not None and env_var_path is not None:
                    logger.warning(f'Environment variable {env_var} set to ' +
                                   f'non-existant path: {rc_path}')
                raise ApplicationError(f'Missing option {lopt}')
            else:
                modified_config = self._load()
        else:
            modified_config = self._load()
        return modified_config

    def __call__(self) -> Configurable:
        return self.merge()


@dataclass
class ConfigurationOverrider(object):
    """Overrides configuration in the app config.  This is useful for replacing on
    a per command line invocation basis.  Examples could include changing the
    number of epochs trained for a model.

    The :obj:`override` field either contains a path to a file that contains
    the configuration file to use to clobber the given sections/values, or a
    string to be interpreted by :class:`.StringConfig`.  This determination is
    made by whether or not the string points to an existing file or directory.

    """
    OVERRIDE_PATH_FIELD = 'override'
    CLI_META = {'first_pass': True,  # not a separate action
                'mnemonic_includes': {'merge'},
                # better/shorter  long name, and reserve the short name
                'option_overrides': {OVERRIDE_PATH_FIELD:
                                     {'metavar': '<FILE|DIR|STRING>',
                                      'short_name': None}},
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'option_includes': {OVERRIDE_PATH_FIELD}}

    config: Configurable = field()
    """The parent configuration, which is populated from the child configuration
    (see class docs).

    """

    override: str = field(default=None)
    """A config file/dir or a comma delimited section.key=value string that
    overrides configuration."""

    def merge(self) -> Configurable:
        """Merge the string configuration with the application context."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'overriding with: {self.override}')
        if self.override is not None:
            path = Path(self.override)
            if path.exists():
                cf = ConfigurableFactory()
                overrides = cf.from_path(path)
            else:
                overrides = StringConfig(self.override)
            self.config.merge(overrides)
        return self.config

    def __call__(self) -> Configurable:
        return self.merge()
