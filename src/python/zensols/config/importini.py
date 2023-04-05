"""Contains a class for importing child configurations.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Iterable, Tuple, List, Dict, Any, Set, Sequence, Union
import logging
from itertools import chain
from collections import ChainMap
from pathlib import Path
from configparser import (
    ConfigParser, ExtendedInterpolation, InterpolationMissingOptionError
)
from zensols.introspect import ClassImporterError
from . import (
    ConfigurableError, ConfigurableFileNotFoundError,
    Configurable, ConfigurableFactory, IniConfig, ImportYamlConfig, rawconfig,
)

logger = logging.getLogger(__name__)


class _ParserAdapter(object):
    """Adapts a :class:`~configparser.ConfigParser` to a :class:`.Configurable`.

    """
    def __init__(self, conf: Configurable, defs: Dict[str, str]):
        self.conf = conf
        self.defs = defs

    def get(self, section: str, option: str, *args, **kwags):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f'get ({type(self.conf).__name__}): {section}:{option}')
        if self.conf.has_option(option, section):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('contains option')
            val = self.conf.get_option(option, section)
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'option not found, trying defs: {self.defs}')
            val = self.defs.get(f'{section}:{option}')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'using defaults value: {val}')
            if val is None:
                # raise an InterpolationMissingOptionError
                try:
                    self.conf.get_option(option, section)
                except ConfigurableError as e:
                    raise ConfigurableError(
                        f'Can not get option {section}:{option}') from e
        return val

    def optionxform(self, option: str) -> str:
        return option.lower()

    def items(self, section: str, raw: bool = False):
        return self.conf.get_options(section)

    def __str__(self) -> str:
        return str(self.conf.__class__.__name__)

    def __repr__(self) -> str:
        return self.__str__()


class _SharedExtendedInterpolation(ExtendedInterpolation):
    """Adds other :class:`Configurable` instances to available parameter to
    substitute.

    """
    def __init__(self, children: Tuple[Configurable, ...],
                 robust: bool = False):
        super().__init__()
        defs = {}
        for child in children:
            with rawconfig(child):
                for sec in child.sections:
                    for k, v in child.get_options(sec).items():
                        defs[f'{sec}:{k}'] = v
        self.children = tuple(map(lambda c: _ParserAdapter(c, defs), children))
        self.robust = robust

    def before_get(self, parser: ConfigParser, section: str, option: str,
                   value: str, defaults: ChainMap):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'before_get: section: {section}:{option}: {value}')
        res = value
        last_ex = None
        parsers = tuple(chain.from_iterable([[parser], self.children]))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'defaults: {defaults}')
        for pa in parsers:
            try:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'inter: {pa}: {section}:{option} = {value}')
                res = super().before_get(pa, section, option, value, defaults)
                last_ex = None
                break
            except InterpolationMissingOptionError as e:
                last_ex = e
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'missing option: {e}')
        if (not self.robust) and (last_ex is not None):
            msg = f'can not set {section}:{option} = {value}: {last_ex}'
            raise ConfigurableError(msg)
        return res


class _BootstrapConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    :class:`~configparser.ExtendedInterpolation`.  One of these is created
    every time an instance of :class:`.ImportIniConfig` is created, which
    includes nested configruation imports when we *descend* recursively.

    """
    def __init__(self, parent: IniConfig, children: Tuple[Configurable, ...]):
        """Initialize.

        :param parent: the initial config having only the import, load and
                       reference sections

        :param children: the children initialized with
                         :class:`.ImportIniConfig`, which are later used to
                         copy forward configuration as configurations are
                         loaded

        """
        super().__init__(parent, parent.default_section)
        self.children = [parent] + list(children)

    def append_child(self, child: Configurable):
        self.children.append(child)
        for c in self.children:
            with rawconfig(c):
                c.copy_sections(self)

    def _create_config_parser(self) -> ConfigParser:
        parser = ConfigParser(
            interpolation=_SharedExtendedInterpolation(self.children))
        with rawconfig(self.config_file):
            for sec in self.config_file.sections:
                parser.add_section(sec)
                for k, v in self.config_file.get_options(sec).items():
                    parser.set(sec, k, v)
        return parser

    def _create_and_load_parser(self, parser: ConfigParser):
        # skip reloading, as that was done when the parser was created
        pass


class ImportIniConfig(IniConfig):
    """A configuration that uses other :class:`.Configurable` classes to load other
    sections.  A special ``import`` section is given that indicates what other
    sections to load as children configuration.  Each of those indicated to
    import are processed in order by:

      1. Creating the delegate child :class:`Configurable` given in the
         section.

      2. Copying all sections from child instance to the parent.

      3. Variable interpolation as a function of
         :class:`~configparser.ConfigParser` using
         :class:`~configparser.ExtendedInterpolation`.

    The ``import`` section has a ``sections`` entry as list of sections to
    load, a ``references`` entry indicating which sections to provide as
    children sections in child loaders, a ``config_file`` and ``config_files`
    entries to load as children directly.

    For example::

        [import]
        references = list: default, package, env
        sections = list: imp_obj

        [imp_obj]
        type = importini
        config_file = resource: resources/obj.conf

    This configuration loads a resource import INI, which is an implementation
    of this class, and provides sections ``default``, ``package`` and ``env``
    for any property string interpolation while loading ``obj.conf``.

    See the `API documentation
    <https://plandes.github.io/util/doc/config.html#import-ini-configuration>`_
    for more information.

    """
    IMPORT_SECTION = 'import'
    SECTIONS_SECTION = 'sections'
    SINGLE_CONFIG_FILE = ConfigurableFactory.SINGLE_CONFIG_FILE
    CONFIG_FILES = 'config_files'
    REFS_NAME = 'references'
    CLEANUPS_NAME = 'cleanups'
    TYPE_NAME = ConfigurableFactory.TYPE_NAME
    _IMPORT_SECTION_FIELDS = {SECTIONS_SECTION, SINGLE_CONFIG_FILE,
                              CONFIG_FILES, REFS_NAME, CLEANUPS_NAME}

    def __init__(self, *args,
                 config_section: str = IMPORT_SECTION,
                 exclude_config_sections: bool = True,
                 children: Tuple[Configurable, ...] = (),
                 use_interpolation: bool = True,
                 **kwargs):
        """Initialize.

        :param config_file: the configuration file path to read from

        :param default_section: default section (defaults to `default`)

        :param robust: if `True`, then don't raise an error when the
                       configuration file is missing

        :param config_section: the name of the section that has the
                               configuration (i.e. the ``sections`` entry)

        :param exclude_config_sections:
             if ``True``, the import and other configuration sections are
             removed

        :param children: additional configurations used both before and after
                         bootstrapping

        :param use_interpolation: if ``True``, interpolate variables using
                                  :class:`~configparser.ExtendedInterpolation`

        """
        super().__init__(*args, use_interpolation=use_interpolation, **kwargs)
        self.config_section = config_section
        self.exclude_config_sections = exclude_config_sections
        if children is None:
            self._raise('Missing importini children')
        self.children = children
        if exclude_config_sections and \
           (self.default_section == self.config_section):
            self._raise('You must set exclude_config_sections to False ' +
                        'when the import and config section are the same')

    def _get_bootstrap_config(self) -> _BootstrapConfig:
        """Create the config that is used to read only the sections needed to
        import/load other configuration.  This adds the import section, any
        sections it *refers* to, and the sections it indicates to load.

        References are those needed to continue parsing the rest of the boot
        strap configuration for this instance.  This usually includes a
        ``default`` section that might have a ``resources`` property used to
        populate a load section paths.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('creating bootstrap parser')
        conf_sec = self.config_section
        bs_config = IniConfig(self.config_file)
        cparser = bs_config.parser
        has_secs = bs_config.has_option(self.SECTIONS_SECTION, conf_sec)
        has_refs = bs_config.has_option(self.REFS_NAME, conf_sec)
        # add sections and references to the temporary config
        if has_secs or has_refs:
            secs = set()
            # add load sections
            if has_secs:
                sec_lst: List[Union[str, Path]] = self.serializer.parse_object(
                    bs_config.get_option(self.SECTIONS_SECTION, conf_sec))
                secs.update(set(sec_lst))
            # add references
            if has_refs:
                refs: List[Union[str, Path]] = self.serializer.parse_object(
                    bs_config.get_option(self.REFS_NAME, conf_sec))
                secs.update(set(refs))
            # add the import section itself, used later to load children config
            secs.add(conf_sec)
            # remove all sections but import, load and reference from the
            # parser
            to_remove = set(bs_config.sections) - secs
            for r in to_remove:
                cparser.remove_section(r)
        return _BootstrapConfig(bs_config, self.children)

    def _validate_bootstrap_config(self, config: Configurable):
        """Validate that the import section doesn't have bad configuration."""
        conf_sec: str = self.config_section
        if conf_sec in config.sections:
            import_sec: Dict[str, str] = config.populate({}, conf_sec)
            import_props: Set[str] = set(import_sec.keys())
            refs: List[str] = import_sec.get(self.REFS_NAME)
            file_props: Set[str] = {self.SINGLE_CONFIG_FILE, self.CONFIG_FILES}
            aliens = import_props - self._IMPORT_SECTION_FIELDS
            if len(aliens) > 0:
                props = ', '.join(map(lambda p: f"'{p}'", aliens))
                self._raise(f"Invalid options in section '{conf_sec}'" +
                            f": {props}")
            if len(file_props & import_props) == 2:
                self._raise(
                    f"Cannot have both '{self.SINGLE_CONFIG_FILE}' " +
                    f"and '{self.CONFIG_FILES}' in section '{conf_sec}'")
            if refs is not None:
                for ref in refs:
                    if ref not in config.sections:
                        self._raise(
                            f"Reference '{ref}' in section '{conf_sec}' not " +
                            f"found, got: {set(config.sections)}")

    def _create_config(self, section: str,
                       params: Dict[str, Any]) -> Configurable:
        """Create a config from a section."""
        return ConfigurableFactory.from_section(params, section)

    def _create_configs(self, section: str, params: Dict[str, Any],
                        bs_config: _BootstrapConfig) -> List[Configurable]:
        """Create one or more :class:`~zensols.config.Configuration` instance depending
        on if one or more configuration files are given.  Configurations are
        created with using a :class:`~zensols.config.ConfigurationFactory` in
        :meth:`_create_config`.  This method is called once to create all
        configuration files for obj:`CONFIG_FILES` and again for each section
        for :obj:`SECTIONS_SECTION`.

        :param section: the import ini section to load

        :param params: the section options/properties

        :param bs_config: the bootstrap loader created in
                          :meth:`_get_bootstrap_config`

        """
        configs: List[Configurable] = []
        conf_files: List[str] = params.get(self.CONFIG_FILES)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'creating configs from section: [{section}]')
        if conf_files is None:
            try:
                # create a configuration from the section as a section load
                configs.append(self._create_config(section, params))
            except ClassImporterError as e:
                raise ConfigurableError(
                    f"Could not import section '{section}': {e}") from e
        else:
            # otherwise, synthesize a section load for each given config file
            sparams = dict(params)
            del sparams[self.CONFIG_FILES]
            try:
                for cf in conf_files:
                    parsed_cf = self.serializer.parse_object(cf)
                    # skip Nones substituted by introplation (like when
                    # ConfigurationImporter subtitutues a missing config file)
                    if parsed_cf is not None:
                        sparams[self.SINGLE_CONFIG_FILE] = parsed_cf
                        conf = self._create_config(section, sparams)
                        configs.append(conf)
            except ClassImporterError as e:
                raise ConfigurableError(
                    f"Could not import '{cf}' in section '{section}': {e}") \
                    from e
        # add configurations as children to the bootstrap config
        for config in configs:
            # recursively create new import ini configs and add the children
            # we've created thus far for forward interpolation capability
            if isinstance(config, (ImportIniConfig, ImportYamlConfig)):
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f'descending: {config}')
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f'adding bootstrap {bs_config.children} + ' +
                                f'self {self.children} to {config}')
                # add children bootstrap config that aren't add duplicates
                # children created with this instance
                ids: Set[int] = set(map(lambda c: id(c), bs_config.children))
                new_children = list(bs_config.children)
                new_children.extend(
                    tuple(filter(lambda c: id(c) not in ids, self.children)))
                config.children = tuple(new_children)
            # add the configurable to the bootstrap config
            bs_config.append_child(config)
        return configs

    def _get_children(self) -> Tuple[List[str], Iterable[Configurable]]:
        """"Get children used for this config instance.  This is done by import each
        import section and files by delayed loaded for each.

        Order is important as each configuration can refer to previously loaded
        configurations.  For this reason, the :class:`_ConfigLoader` is needed
        to defer loading: one for loading sections, and one for loading file.

        """
        # guard on OS level config file since the super class allows different
        # types such as directory; we only deal with files in this class
        if isinstance(self.config_file, Path) and \
           not self.config_file.is_file():
            raise ConfigurableFileNotFoundError(self.config_file)
        # create the bootstrap config used to start the import process
        bs_config: _BootstrapConfig = self._get_bootstrap_config()
        conf_sec: str = self.config_section
        conf_secs: Set[str] = {conf_sec}
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'parsing section: {conf_sec}')
        # look for bad configuration in the import section
        self._validate_bootstrap_config(bs_config)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating children for: {conf_sec}')
        # first load files given in the import section
        if bs_config.has_option(self.SINGLE_CONFIG_FILE, conf_sec):
            fname: Union[Path, str] = self.serializer.parse_object(
                bs_config.get_option(self.SINGLE_CONFIG_FILE, conf_sec))
            params = {self.SINGLE_CONFIG_FILE: fname}
            self._create_configs('<no section>', params, bs_config)
        elif bs_config.has_option(self.CONFIG_FILES, conf_sec):
            sec = bs_config.populate(section=conf_sec)
            fnames: List[str] = self.serializer.parse_object(
                bs_config.get_option(self.CONFIG_FILES, conf_sec))
            for fname in fnames:
                # enable resource descriptors
                fname: Any = self.serializer.parse_object(fname)
                params = {self.SINGLE_CONFIG_FILE: fname}
                self._create_configs('<no section>', params, bs_config)
        # load each import section, again in order
        if bs_config.has_option(self.SECTIONS_SECTION, conf_sec):
            secs: List[Union[Path, str]] = self.serializer.parse_object(
                bs_config.get_option(self.SECTIONS_SECTION, conf_sec))
            for sec in secs:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"populating section '{sec}', {bs_config.children}")
                conf_secs.add(sec)
                params = bs_config.populate({}, section=sec)
                self._create_configs(sec, params, bs_config)
        # allow the user to remove more sections after import
        if bs_config.has_option(self.CLEANUPS_NAME, conf_sec):
            cleanups: Sequence[str] = self.serializer.parse_object(
                bs_config.get_option(self.CLEANUPS_NAME, conf_sec))
            conf_secs.update(cleanups)
        return conf_secs, bs_config.children

    def _load_imports(self, parser: ConfigParser):
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'importing {self._get_container_desc()}, ' +
                        f'children={self.children}')
        csecs, children = self._get_children()
        overwrites: Set = set()
        # copy each configuration added to the bootstrap loader in the order we
        # added them.
        c: Configurable
        for c in children:
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'loading configuration {c} -> {self}')
            par_secs: List[str] = parser.sections()
            sec: str
            # copy every section from the child to target our new parser
            for sec in c.sections:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'importing section {c}:[{sec}]')
                if sec not in par_secs:
                    parser.add_section(sec)
                # assume everything is resolvable as this is the last step in
                # the loading of this instance
                try:
                    opts = c.get_options(sec)
                except InterpolationMissingOptionError as e:
                    msg = f'Could not populate {c}:[{sec}]: {e}'
                    self._raise(msg, e)
                for k, v in opts.items():
                    key = f'{sec}:{k}'
                    has = parser.has_option(sec, k)
                    fv = self._format_option(k, v, sec)
                    # overwrite the option/property when not yet set or its
                    # already by overwriten by a previous child; however, don't
                    # set it when its new per this instance's import iteration
                    if not has or key in overwrites:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'overwriting {sec}:{k}: {v} -> {fv}')
                        parser.set(sec, k, fv)
                        overwrites.add(key)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'imported {len(children)} children to {self}')
        if self.exclude_config_sections:
            self._config_sections = csecs

    def _create_and_load_parser(self, parser: ConfigParser):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('creating and loading parser')
        super()._create_and_load_parser(parser)
        self._load_imports(parser)
        if hasattr(self, '_config_sections'):
            for sec in self._config_sections:
                parser.remove_section(sec)
            del self._config_sections
        del self.children
        return parser
