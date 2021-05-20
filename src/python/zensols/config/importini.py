from __future__ import annotations
"""Contains a class for importing child configurations.

"""
__author__ = 'Paul Landes'

from typing import Iterable, Tuple, List, Dict, Any
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
    Configurable, ConfigurableFactory, IniConfig
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
                self.conf.get_option(option, section)
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

    def append_child(self, child: Configurable):
        self.children.append(child)
        for c in self.children:
            c.copy_sections(self)

    def _create_and_load_parser(self) -> ConfigParser:
        parser = ConfigParser(
            defaults=self.create_defaults,
            interpolation=_SharedExtendedInterpolation(self.children))
        parser.read_file(self.config)
        return parser


@dataclass
class _ConfigLoader(object):
    """Loads/creates instances of :class:`.Configurable`.

    :see: :meth:`.ImportIniConfig._get_children`

    """
    section: str
    factory: ConfigurableFactory = field(repr=False)
    method: str
    value: Any

    def __call__(self, children: List[Configurable]) -> Configurable:
        meth = getattr(self.factory, self.method)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'Invoking {meth} with {self.value}')
        return meth(self.value)


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

    A section called ``import`` is used to load other configuration.  This is
    either done by loading it:

      * ``files`` entry in the section to load a list of files; ``type`` can be
        given to select the loader (see :class:`.ConfigurableFactory`)

      * ``

    """
    IMPORT_SECTION = 'import'
    SECTIONS_SECTION = 'sections'
    SINGLE_CONFIG_FILE = 'config_file'
    CONFIG_FILES = 'files'
    REFS_SECTION = 'references'

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

        :param create_defaults: used to initialize the configuration parser,
                                and useful for when substitution values are
                                baked in to the configuration file

        :param config_section: the name of the section that has the
                               configuration (i.e. the ``sections`` entry)

        :param exclude_config_sections:
             if ``True``, the import and other configuration sections are
             removed

        :param children: additional configurations used both before and after
                         bootstrapping

        """
        super().__init__(*args, **kwargs)
        self.config_section = config_section
        self.exclude_config_sections = exclude_config_sections
        self.children = children
        self.use_interpolation = use_interpolation
        if exclude_config_sections and \
           (self.default_section == self.config_section):
            raise ConfigurableError(
                'You must set exclude_config_sections to False when the ' +
                'import and config section are the same')

    def _get_bootstrap_parser(self) -> _StringIniConfig:
        """Create the config that is used to read only the sections needed to
        import/load other configuration.

        """
        logger.debug('creating bootstrap parser')
        conf_sec = self.config_section
        parser = IniConfig(self.config_file)
        cparser = parser.parser
        has_refs = parser.has_option(self.REFS_SECTION, conf_sec)
        has_secs = parser.has_option(self.SECTIONS_SECTION, conf_sec)
        if has_secs or has_refs:
            secs = set()
            if has_secs:
                secs.update(set(
                    parser.get_option_list(self.SECTIONS_SECTION, conf_sec)))
            if has_refs:
                csecs = parser.get_option_list(self.REFS_SECTION, conf_sec)
                secs.update(set(csecs))
            secs.add(conf_sec)
            to_remove = set(parser.sections) - secs
            for r in to_remove:
                cparser.remove_section(r)
        sconf = StringIO()
        cparser.write(sconf)
        sconf.seek(0)
        return _StringIniConfig(sconf, parser, self.children)

    def _create_single_loader(self, section: str, params: Dict[str, Any]) -> \
            _ConfigLoader:
        """Create a config loader from a section."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'section: {section}, params: {params}')
        params = dict(params)
        cf = ConfigurableFactory(params)
        class_name = params.get('class_name')
        tpe = params.get('type')
        config_file = params.get(self.SINGLE_CONFIG_FILE)
        loader: _ConfigLoader
        if class_name is not None:
            del params['class_name']
            loader = _ConfigLoader(section, cf, 'from_class_name', class_name)
        elif tpe is not None:
            del params['type']
            loader = _ConfigLoader(section, cf, 'from_type', tpe)
        elif config_file is not None:
            del params[self.SINGLE_CONFIG_FILE]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f'getting instance using config factory: {config_file}')
            loader = _ConfigLoader(section, cf, 'from_path', Path(config_file))
        return loader

    def _create_loader(self, section: str, params: Dict[str, Any]) -> \
            List[_ConfigLoader]:
        """Create either a single config loader if the section defines one, or many if
        a list of files are given in the section.

        """
        conf_files = params.get(self.CONFIG_FILES)
        loaders = []
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating and loading parser: {section}')
        if conf_files is None:
            loaders.append(self._create_single_loader(section, params))
        else:
            sparams = dict(params)
            del sparams[self.CONFIG_FILES]
            for cf in conf_files:
                sparams[self.SINGLE_CONFIG_FILE] = cf
                conf = self._create_single_loader(section, sparams)
                loaders.append(conf)
        return loaders

    def _load(self, loaders: List[_ConfigLoader], children: List[Configurable],
              parser: _StringIniConfig):
        """Load each configuration from the loader."""
        for loader in loaders:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'loading {loader}')
            inst = loader(children)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'created instance: {type(inst)}')
            if isinstance(inst, self.__class__):
                new_children = list(inst.children)
                new_children.extend(self.children)
                new_children.extend(children)
                inst.children = tuple(new_children)
            parser.append_child(inst)
        loaders.clear()

    def _get_children(self) -> Tuple[List[str], Iterable[Configurable]]:
        """"Get children used for this config instance.  This is done by import each
        import section and files by delayed loaded for each.

        Order is important as each configuration can refer to previously loaded
        configurations.  For this reason, the :class:`_ConfigLoader` is needed
        to defer loading: one for loading sections, and one for loading file.

        """
        logger.debug('get children')
        if isinstance(self.config_file, Path) and \
           not self.config_file.is_file():
            raise ConfigurableFileNotFoundError(self.config_file)
        conf_sec: str = self.config_section
        parser: _StringIniConfig = self._get_bootstrap_parser()
        children: List[Configurable] = parser.children
        conf_secs: List[str] = [conf_sec]
        loaders: List[_ConfigLoader] = []
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating children for: {conf_sec}')
        # first load files given in the import section
        if parser.has_option(self.CONFIG_FILES, conf_sec):
            for fname in parser.get_option_list(self.CONFIG_FILES, conf_sec):
                params = {self.SINGLE_CONFIG_FILE: fname}
                loaders.extend(self._create_loader('<no section>', params))
                self._load(loaders, children, parser)
        # load each import section, again in order
        if parser.has_option(self.SECTIONS_SECTION, conf_sec):
            for sec in parser.get_option_list(self.SECTIONS_SECTION, conf_sec):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'populating section {sec}, {children}')
                conf_secs.append(sec)
                params = parser.populate({}, section=sec)
                loaders.extend(self._create_loader(sec, params))
                self._load(loaders, children, parser)
        return conf_secs, children

    def _create_config_parser(self) -> ConfigParser:
        logger.debug('createing loader parser')
        csecs, children = self._get_children()
        if self.use_interpolation:
            parser = ConfigParser(
                defaults=self.create_defaults,
                interpolation=ExtendedInterpolation())
        else:
            parser = ConfigParser(defaults=self.create_defaults)
        for c in children:
            par_secs = parser.sections()
            for sec in c.sections:
                if sec not in par_secs:
                    parser.add_section(sec)
                for k, v in c.get_options(sec).items():
                    v = self._format_option(k, v, sec)
                    parser.set(sec, k, v)
        if self.exclude_config_sections:
            self._config_sections = csecs
        return parser

    def _create_and_load_parser(self) -> ConfigParser:
        logger.debug('creating and loading parser')
        parser = super()._create_and_load_parser()
        if hasattr(self, '_config_sections'):
            for sec in self._config_sections:
                parser.remove_section(sec)
            del self._config_sections
        del self.children
        return parser
