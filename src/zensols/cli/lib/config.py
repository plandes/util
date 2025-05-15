"""Configuration merging first pass applications.  These utility applications
allow a configuration option and then merge that configuration with the
application context.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Set, List, Tuple, Iterable, Optional, Type, Union
from dataclasses import dataclass, field
import os
import logging
from string import Template
import parse as par
import re
from pathlib import Path
import pickle
from zensols.util import PackageResource
from zensols.persist import persisted
from zensols.config import (
    rawconfig, Configurable, ConfigurableFactory,
    IniConfig, ImportIniConfig, StringConfig, DictionaryConfig,
)
from .. import (
    Dictable, ActionCliError, ApplicationError, OptionMetaData, ActionMetaData,
    ApplicationObserver, Action, Application,
)

logger = logging.getLogger(__name__)


class _ConfiguratorImporterTemplate(Template):
    delimiter = '^'


class _PreLoadImportIniConfig(ImportIniConfig):
    _PRELOAD_FORMAT = 'preload:{}'

    def __init__(self, *args, preloads: Dict[str, Configurable], **kwargs):
        super().__init__(*args, **kwargs)
        self.preloads = preloads

    @classmethod
    def format_preload(self, name: str) -> str:
        return self._PRELOAD_FORMAT.format(name)

    @classmethod
    def parse_preload(self, s: str) -> Optional[str]:
        pres: par.Result = par.parse(self._PRELOAD_FORMAT, s)
        if pres is not None:
            return pres[0]

    def _create_config(self, section: str,
                       params: Dict[str, Any]) -> Configurable:
        conf: Configurable = None
        key: str = None
        config_file: Union[Path, str] = params.get(self.SINGLE_CONFIG_FILE)
        if isinstance(config_file, str):
            key = self.parse_preload(config_file)
        if key is not None:
            conf = self.preloads.get(key)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"create config '{key} -> {conf} ({type(conf)})")
            if conf is None:
                logger.warning(f"matched a preload format '{config_file}' " +
                               f"with non-existing preload: '{key}'")
        if conf is None:
            conf = super()._create_config(section, params)
        return conf


@dataclass
class ConfigurationOverrider(object):
    """Overrides configuration in the app config.  This is useful for replacing
    on a per command line invocation basis.  Examples could include changing the
    number of epochs trained for a model.

    The :obj:`override` field either contains a path to a file that contains
    the configuration file to use to clobber the given sections/values, or a
    string to be interpreted by :class:`.StringConfig`.  This determination is
    made by whether or not the string points to an existing file or directory.

    """
    OVERRIDE_FIELD = 'override'
    CLI_META = {'first_pass': True,  # not a separate action
                'mnemonic_includes': {'merge'},
                # better/shorter  long name, and reserve the short name
                'option_overrides': {OVERRIDE_FIELD:
                                     {'metavar': '<FILE|DIR|STRING>',
                                      'short_name': None}},
                # only the path to the configuration should be exposed as a
                # an option on the comamnd line
                'option_includes': {OVERRIDE_FIELD}}

    config: Configurable = field()
    """The parent configuration, which is populated from the child configuration
    (see class docs).

    """
    override: str = field(default=None)
    """A config file/dir or a comma delimited section.key=value string that
    overrides configuration.

    """
    option_sep_regex: str = field(default=r'\s*,\s*')
    """The string used to delimit the each key/value pair."""

    disable: bool = field(default=False)
    """Whether to disable the application, which is useful to set to ``False``
    when used with :class:`.ConfigurationImporter`.

    """
    def get_configurable(self) -> Optional[Configurable]:
        if self.override is not None:
            path = Path(self.override)
            if path.exists():
                cf = ConfigurableFactory()
                overrides = cf.from_path(path)
            else:
                overrides = StringConfig(
                    self.override,
                    option_sep_regex=self.option_sep_regex
                )
            return overrides

    def merge(self) -> Configurable:
        """Merge the string configuration with the application context."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'overriding with: {self.override}')
        if not self.disable:
            conf: Optional[Configurable] = self.get_configurable()
            if conf is not None:
                self.config.merge(conf)
        return self.config

    def __call__(self) -> Configurable:
        return self.merge()


@dataclass
class _CacheConfigManager(object):
    path: Path = field()
    config: ImportIniConfig = field()
    watch_files: Dict[Path, int] = field(default_factory=dict)

    def _get_newer_files(self, files: Dict[Path, int]) -> Iterable[Path]:
        path: Path
        prev_mtime: int
        for path, prev_mtime in files.items():
            cur_mtime = path.stat().st_mtime
            if cur_mtime > prev_mtime:
                yield path

    def load(self) -> ImportIniConfig:
        prev_config: ImportIniConfig = None
        if self.path.is_file():
            with open(self.path, 'rb') as f:
                prev_mng: _CacheConfigManager = pickle.load(f)
            newer_files: Tuple[Path, ...] = tuple(
                self._get_newer_files(prev_mng.watch_files))
            if len(newer_files) == 0:
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f'reusing cached config: {self.path}')
                prev_config = prev_mng.config
            else:
                if logger.isEnabledFor(logging.INFO):
                    fnames: str = ', '.join(map(str, newer_files))
                    logger.info(f'reloading since files changed: {fnames}')
        if prev_config is None:
            self.config.start_file_capture()
        return prev_config

    def save(self):
        visited: Set[Path] = set(self.config.stop_file_capture())
        self.watch_files.update(dict(map(
            lambda p: (p, p.stat().st_mtime), visited)))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'wb') as f:
            pickle.dump(self, f)


@dataclass
class ConfigurationImporter(ApplicationObserver, Dictable):
    """This class imports a child configuration in to the application context.
    It does this by:

      1. Attempt to load the configuration indicated by the ``--config``
         option.

      2. If the option doesn't exist, attempt to get the path to load from an
         environment variable (see :meth:`get_environ_var_from_app`).  For
         example, for package ``zensols.util``, the environment variable
         ``UTILRC`` environment variable's path is used.

      3. If the environment variable is not found, then look for the UNIX style
         resource file (see :meth:`get_environ_path`).  For example, package
         ``zensols.util`` would point to ``~/.utilrc``.

      4. Loads the *child* configuration.

      5. Copy all sections from the child configuration to :obj:`config`.

    The child configuration is created by :class:`.ConfigurableFactory`.  If
    the child has a `.conf` extension, :class:`.ImportIniConfig` is used with
    its child set as :obj:`config` so the two can reference each other at
    property/factory resolve time.

    Special mnemonic ``^{config_path}`` can be used in an
    :class`.ImportIniConfig` import section in the `config_files` property to
    load the referred configuration file in any order with the other loaded
    files.  The special mnemonic ``^{override}`` does the same thing with the
    :class:`.ConfigurationOverrider` one pass application as well.

    """
    _OVERRIDES_KEY = ConfigurationOverrider.OVERRIDE_FIELD
    _OVERRIDES_PRELOAD = _PreLoadImportIniConfig.format_preload(_OVERRIDES_KEY)

    CONFIG_PATH_FIELD = 'config_path'
    """The field name in this class of the child configuration path.

    :see: :obj:`config_path`

    """
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
    """The string value of the ``type`` parameter in the section config
    identifying an :class:`.ImportIniConfig` import section.

    """
    ENVIRON_SHARED_NAME = 'ZENSOLSRC'
    """Environment variable name that points to a directory for shared config
    files (see :meth:`get_environ_path`).

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
    """If ``True``, raise an :class:`.ApplicationError` if the option is not
    given.

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
    """Additional which section to load as an import.  This is only valid and
    used when :obj:`type` is set to `import`.  When it is, the section will
    replace the string ``^{config_apth}`` (and any other field in this instance
    using the same syntax) and load indicated remaining configuration using
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

    cache_path: Path = field(default=None)
    """A path to a binary file of the cached configuration.  This is useful for
    large application contexts that have a lot of imports that take a long time
    to load.

    When this file is set, the imported configuration files and their modify
    timestamps are written along with the loaded configuration to this specified
    file.  On subsequent runs, previous configuration is used if none of the
    configuration files have changed.  Otherwise, they are reloaded and cached
    again.

    """
    # name of this field must match
    # :obj:`ConfigurationImporter.CONFIG_PATH_FIELD`
    config_path: Path = field(default=None)
    """The configuration file."""

    @persisted('_rc_prefix')
    def _get_rc_prefix(self) -> str:
        """Return the resource prefix.  For example, if the package resource is
        ``zensols.util`` the outupt is ``util``.

        """
        pkg_res: PackageResource = self._app.factory.package_resource
        name: str = pkg_res.name
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"match environment variable '{name}' " +
                         f'on {self.ENVIRON_VAR_REGEX}')
        m = self.ENVIRON_VAR_REGEX.match(name)
        if m is not None:
            name = m.group(1)
        return name

    def get_environ_var_from_app(self) -> str:
        """Return the environment variable based on the name of the application.
        This returns the :obj:`config_path_environ_name` if set, otherwise, it
        generates it based on the name returned from the packge + ``RC`` and
        capitalizes it.

        """
        name: str
        if self.config_path_environ_name is not None:
            name = self.config_path_environ_name
        else:
            name = f'{self._get_rc_prefix()}rc'.upper()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"using environment variable '{name}'")
        return name

    def get_environ_path(self) -> Optional[Path]:
        """Return the path to the resource configuration file.  The following
        files are searched in order:

          1. This first uses :meth:`get_environ_var_from_app` to attempt to find
             an environment variable with a reference to file,

          2. A file pointed by the environment variable
             ``ENVIRON_SHARED_NAME/<application prefix>`` *without* the trailing
             ``rc`` (i.e. package ``zensols.util`` would point to
             ``~/etc/util.{conf,yml}``),

          3. UNIX style file naming conventionsin the home directory
             (i.e. package ``zensols.util`` would point to ``~/.utilrc``).

        """
        rc_files: List[Path] = []
        env_var: str = self.get_environ_var_from_app()
        env_var_path: str = os.environ.get(env_var)
        prefix: str = self._get_rc_prefix()
        home_rc_path: Path = Path(f'~/.{prefix}rc').expanduser()
        shared_rc_var: str = os.environ.get(self.ENVIRON_SHARED_NAME)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('loading config from environment ' +
                         f"varaibles '{env_var}' = {env_var_path}")
        if env_var_path is not None:
            rc_files.append(Path(env_var_path))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                'loading config from environment referred shared directory ' +
                f"'{self.ENVIRON_SHARED_NAME}' = '{shared_rc_var}'")
        if shared_rc_var is not None:
            sdir: Path = Path(shared_rc_var)
            rc_files.append((sdir / f'{prefix}.conf').expanduser())
            rc_files.append((sdir / f'{prefix}.yml').expanduser())
        if home_rc_path.is_file():
            rc_files.append(home_rc_path)
        path: Path
        for path in rc_files:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'checking for RC file: {path}')
            if path.is_file():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'found RC file: {path}')
                return path

    def _get_config_option(self) -> str:
        """Return the long option name (with dashes) as given on the command
        line.

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

    def _get_override_config(self) -> Configurable:
        conf: Configurable = None
        ac: Action
        for ac in self._app.actions:
            ctype: Type = ac.class_meta.class_type
            if issubclass(ctype, ConfigurationOverrider):
                opts: Dict[str, Any] = ac.command_action.options
                sconf: str = opts.get(ConfigurationOverrider.OVERRIDE_FIELD)
                params = {ConfigurationOverrider.OVERRIDE_FIELD: sconf}
                co = ConfigurationOverrider(self.config, **params)
                conf = co.get_configurable()
                break
        if conf is None:
            conf = DictionaryConfig(parent=self.config)
        return conf

    def _validate(self):
        # the section attribute is only useful for ImportIniConfig imports
        if self.type != self.IMPORT_TYPE and self.section is not None:
            raise ActionCliError("Cannot have a 'section' entry " +
                                 f"without type of '{self.IMPORT_TYPE}'")

    def _populate_import_sections(self, config: Configurable) -> \
            Tuple[Configurable, Set[str]]:
        sec: Dict[str, str] = self.config.get_options(self.section)
        secs: Dict[str, Dict[str, str]] = {}
        populated_sec = {}
        vals = self.asdict()
        vals[self._OVERRIDES_KEY] = self._OVERRIDES_PRELOAD
        for k, v in sec.items():
            populated_sec[k] = v.format(**vals)
        secs[ImportIniConfig.IMPORT_SECTION] = populated_sec
        preload_keys: Set[str] = set()
        if ImportIniConfig.SECTIONS_SECTION in populated_sec:
            sub_secs: List[str] = self.config.serializer.parse_object(
                self.config.get_option(
                    ImportIniConfig.SECTIONS_SECTION, self.section))
            for sec in sub_secs:
                repl_sec: Dict[str, str] = {}
                secs[sec] = repl_sec
                with rawconfig(config):
                    for k, v in config.get_options(sec).items():
                        tpl = _ConfiguratorImporterTemplate(v)
                        try:
                            vr = tpl.substitute(vals)
                        except KeyError as e:
                            raise ActionCliError(
                                f"Bad config load special key {e} in: '{v}'")
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'{sec}:{k}: {v} -> {vr}')
                        pls = self.config.serializer.parse_object(vr)
                        if isinstance(pls, (list, tuple)):
                            pls = map(
                                _PreLoadImportIniConfig.parse_preload, pls)
                            pls = filter(lambda x: x is not None, pls)
                            preload_keys.update(pls)
                        repl_sec[k] = vr
        return DictionaryConfig(secs, parent=self.config), preload_keys

    def _load_configuration(self) -> Configurable:
        """Once we have the path and the class used to load the configuration,
        create the instance and load it.

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
                cl_config = DictionaryConfig(parent=self.config)
            else:
                cl_config = cf.from_path(self.config_path)
                logger.info(f'config loaded {self.config_path} as ' +
                            f'type {cl_config.__class__.__name__}')
        # import using ImportIniConfig as a section
        elif self.type == self.IMPORT_TYPE:
            args: dict = {} if self.arguments is None else self.arguments
            children: Tuple[Configurable, ...] = \
                self._app.factory.children_configs
            ini: IniConfig = IniConfig(self.config, parent=self.config)
            dconf: Configurable
            preload_keys: Set[str]
            dconf, preload_keys = self._populate_import_sections(ini)
            preloads: Dict[str, Configurable] = {}
            if self._OVERRIDES_KEY in preload_keys:
                preloads[self._OVERRIDES_KEY] = self._get_override_config()
            secs_to_del.update(dconf.sections)
            dconf.copy_sections(ini)
            if children is None:
                # unit test cases will not have children configurables
                children = ()
            with rawconfig(ini):
                cl_config = _PreLoadImportIniConfig(
                    preloads=preloads,
                    config_file=ini,
                    children=children,
                    parent=self.config,
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
        modified_config: Configurable = None
        cmng: _CacheConfigManager = None
        loaded: bool = False
        if self.cache_path is not None:
            if isinstance(self.config, ImportIniConfig):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'caching: to {self.cache_path}')
                cmng = _CacheConfigManager(self.cache_path, config=self.config)
                if self.config_path is not None:
                    # TODO: add entry point app.conf to watch files
                    cmng.watch_files[self.config_path] = \
                        self.config_path.stat().st_mtime
                modified_config = cmng.load()
                if modified_config is not None:
                    with rawconfig(modified_config):
                        modified_config.copy_sections(self.config)
                        modified_config = self.config
                    loaded = True
            else:
                logger.warning('configured to cache config at' +
                               f'{self.cache_path} but configuration ' +
                               f'is not ImportIniConfig: {type(self.config)}')
        if modified_config is None:
            modified_config = self._load_configuration()
        if cmng is not None and not loaded:
            cmng.save()
        if self.config_path_option_name is not None:
            val: str
            if self.config_path is None:
                val = 'None'
            else:
                val = f'path: {str(self.config_path)}'
            self.config.set_option(self.config_path_option_name,
                                   val, section=self.name)
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
        rc_path: Path = None
        if self.config_path is None:
            rc_path: Path = self.get_environ_path()
            if rc_path is not None:
                self.config_path = rc_path
            elif self.default is not None:
                if self.default == 'skip':
                    self.config_path = None
                else:
                    self.config_path = self.default
        if self.config_path is None:
            if self.expect:
                long_opt: str = self._get_config_option()
                raise ApplicationError(f'Missing option {long_opt}')
            else:
                modified_config = self._load()
        else:
            modified_config = self._load()
        return modified_config

    def __call__(self) -> Configurable:
        return self.merge()
