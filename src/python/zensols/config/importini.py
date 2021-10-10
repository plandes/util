from __future__ import annotations
"""Contains a class for importing child configurations.

"""
__author__ = 'Paul Landes'

from typing import Iterable, Tuple, List, Dict, Any, Set, Sequence
from dataclasses import dataclass, field
import logging
from itertools import chain
from collections import ChainMap
from io import StringIO, TextIOBase
from pathlib import Path
from configparser import (
    ConfigParser, ExtendedInterpolation, InterpolationMissingOptionError
)
from . import (
    ConfigurableError, ConfigurableFileNotFoundError,
    Configurable, ConfigurableFactory, IniConfig, rawconfig,
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
    def __init__(self, children: Tuple[Configurable], robust: bool = False):
        super().__init__()
        defs = {}
        for child in children:
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


class _StringIniConfig(IniConfig):
    """Configuration class extends using advanced interpolation with
    :class:`~configparser.ExtendedInterpolation`.

    """
    def __init__(self, config: TextIOBase, parent: IniConfig,
                 children: Tuple[Configurable]):
        super().__init__(None, parent.default_section)
        self.config = config
        self.children = [parent] + list(children)
        # self.children = list(children)
        # self.children.append(parent)

    def append_child(self, child: Configurable):
        self.children.append(child)
        for c in self.children:
            c.copy_sections(self)
        # for c in self.children:
        #     with rawconfig(c):
        #         c.copy_sections(self)

    def _create_config_parser(self) -> ConfigParser:
        parser = ConfigParser(
            interpolation=_SharedExtendedInterpolation(self.children))
        parser.read_file(self.config)
        return parser

    def _create_and_load_parser(self, parser: ConfigParser):
        pass


class ImportIniConfig(IniConfig):
    """A configuration that uses other :class:`.Configurable` classes to load other
    sections.  A special ``config`` section is given that indicates what other
    sections to load as children configuration.  Each of those indicated to
    import are processed in order by:

      1. Creating the delegate child :class:`Configurable` given in the
         section,

      2. Copying all sections from child instance to the parent.

      3. Variable interpolation as a function of
         :class:`~configparser.ConfigParser` using
         :class:`~configparser.ExtendedInterpolation`.

    See the `API documentation
    <https://plandes.github.io/util/doc/config.html#import-ini-configuration>`_
    for more information.

    """
    IMPORT_SECTION = 'import'
    SECTIONS_SECTION = 'sections'
    SINGLE_CONFIG_FILE = 'config_file'
    CONFIG_FILES = 'config_files'
    REFS_NAME = 'references'
    CLEANUPS_NAME = 'cleanups'
    TYPE_NAME = 'type'
    _IMPORT_SECTION_FIELDS = {SECTIONS_SECTION, SINGLE_CONFIG_FILE,
                              CONFIG_FILES, REFS_NAME, CLEANUPS_NAME}

    def __init__(self, *args,
                 config_section: str = IMPORT_SECTION,
                 exclude_config_sections: bool = True,
                 children: Tuple[Configurable] = (),
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
        self.children = children
        if exclude_config_sections and \
           (self.default_section == self.config_section):
            raise ConfigurableError(
                'You must set exclude_config_sections to False when the ' +
                'import and config section are the same')

    def _get_bootstrap_config(self) -> _StringIniConfig:
        """Create the config that is used to read only the sections needed to
        import/load other configuration.

        """
        logger.debug('creating bootstrap parser')
        conf_sec = self.config_section
        bs_config = IniConfig(self.config_file)
        cparser = bs_config.parser
        has_refs = bs_config.has_option(self.REFS_NAME, conf_sec)
        has_secs = bs_config.has_option(self.SECTIONS_SECTION, conf_sec)
        if has_secs or has_refs:
            secs = set()
            if has_secs:
                sec_lst: List[str] = self.serializer.parse_object(
                    bs_config.get_option(self.SECTIONS_SECTION, conf_sec))
                secs.update(set(sec_lst))
            if has_refs:
                refs: List[str] = self.serializer.parse_object(
                    bs_config.get_option(self.REFS_NAME, conf_sec))
                secs.update(set(refs))
            secs.add(conf_sec)
            to_remove = set(bs_config.sections) - secs
            for r in to_remove:
                cparser.remove_section(r)
        sconf = StringIO()
        cparser.write(sconf)
        sconf.seek(0)
        return _StringIniConfig(sconf, bs_config, self.children)

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
                        self._raise(f"Reference '{ref}' in section " +
                                    f"'{conf_sec}' not found, got: '{refs}'")

    def _create_config(self, section: str,
                       params: Dict[str, Any]) -> Configurable:
        """Create a config loader from a section."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'section: {section}, params: {params}')
        params = dict(params)
        cf = ConfigurableFactory(params)
        class_name = params.get('class_name')
        tpe = params.get(self.TYPE_NAME)
        config_file = params.get(self.SINGLE_CONFIG_FILE)
        config: Configurable
        if class_name is not None:
            del params['class_name']
            config = cf.from_class_name(class_name)
        elif tpe is not None:
            del params[self.TYPE_NAME]
            config = cf.from_type(tpe)
        elif config_file is not None:
            del params[self.SINGLE_CONFIG_FILE]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f'getting instance using config factory: {config_file}')
            config = cf.from_path(Path(config_file))
        else:
            raise ConfigurableError(
                f"No loader information for '{section}': {params}")
        return config

    def _create_configs(self, section: str, params: Dict[str, Any],
                        bs_config: _StringIniConfig) -> List[Configurable]:
        """Create either a single config loader if the section defines one, or many if
        a list of files are given in the section.

        """
        configs: List[Configurable] = []
        children: List[Configurable] = bs_config.children
        conf_files: List[str] = params.get(self.CONFIG_FILES)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'create loader from section: [{section}]')
        if conf_files is None:
            configs.append(self._create_config(section, params))
        else:
            sparams = dict(params)
            del sparams[self.CONFIG_FILES]
            for cf in conf_files:
                parsed_cf = self.serializer.parse_object(cf)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'file: {cf} -> {parsed_cf}')
                sparams[self.SINGLE_CONFIG_FILE] = parsed_cf
                conf = self._create_config(section, sparams)
                configs.append(conf)
        for cfg in configs:
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'create instance: {type(cfg).__name__}')
            # recursively create new import ini configs and add the children
            # we've created thus far for forward interpolation capability
            if isinstance(cfg, ImportIniConfig):
                new_children = list(children)
                new_children.extend(self.children)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'add {new_children} to {cfg}')
                cfg.children = tuple(new_children)
            # add the configurable to the bootstrap config
            bs_config.append_child(cfg)
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
        bs_config: _StringIniConfig = self._get_bootstrap_config()
        conf_sec: str = self.config_section
        conf_secs: Set[str] = {conf_sec}
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'parsing section: {conf_sec}')
        # look for bad configuration in the import section
        self._validate_bootstrap_config(bs_config)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating children for: {conf_sec}')
        # first load files given in the import section
        if bs_config.has_option(self.CONFIG_FILES, conf_sec):
            fnames: List[str] = self.serializer.parse_object(
                bs_config.get_option(self.CONFIG_FILES, conf_sec))
            for fname in fnames:
                params = {self.SINGLE_CONFIG_FILE: fname}
                self._create_configs('<no section>', params, bs_config)
        # load each import section, again in order
        if bs_config.has_option(self.SECTIONS_SECTION, conf_sec):
            secs: List[str] = self.serializer.parse_object(
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

    def _load_imports(self, bs_config: ConfigParser):
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'importing {self.container_desc}, children={self.children}')
        # pre_exist_children = set(map(id, self.children))
        csecs, children = self._get_children()
        c: Configurable
        # if logger.isEnabledFor(logging.INFO):
        #     logger.info(f'created children: {children}')
        # puts = set()
        for c in children:
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'loading configuration from: {c}')
            # pre_exist = id(c) in pre_exist_children
            par_secs = bs_config.sections()
            for sec in c.sections:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'importing section {c}:[{sec}]')
                if sec not in par_secs:
                    bs_config.add_section(sec)
                for k, v in c.get_options(sec).items():
                    fv = self._format_option(k, v, sec)
                    # has = bs_config.has_option(sec, k)
                    # clobber = not pre_exist or not has
                    # if has and sec == 'vectorizer_manager_set':
                    #     print(f'overwriting {c.__class__.__name__}:{self.config_file}:{sec}:{k} {v} -> [{self.container_desc}]:{fv} pe={pre_exist}, has={has}, clobber={clobber}')
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'{sec}:{k}: {v} -> {fv}')
                    bs_config.set(sec, k, fv)
        if self.exclude_config_sections:
            self._config_sections = csecs

    def _create_and_load_parser(self, parser: ConfigParser):
        logger.debug('creating and loading parser')
        super()._create_and_load_parser(parser)
        self._load_imports(parser)
        if hasattr(self, '_config_sections'):
            for sec in self._config_sections:
                parser.remove_section(sec)
            del self._config_sections
        del self.children
        return parser
