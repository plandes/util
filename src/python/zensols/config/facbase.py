"""Classes that create new instances of classes from application configuration
objects and files.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Any, Type, Optional, Tuple, Dict
from abc import ABC, abstractmethod
from enum import Enum
import logging
import inspect
import copy as cp
from pathlib import Path
import textwrap
from time import time
from zensols.util import APIError
from zensols.introspect import (
    ClassImporter, ClassResolver, DictionaryClassResolver
)
from zensols.config import Configurable

logger = logging.getLogger(__name__)


class FactoryError(APIError):
    """Raised when an object can not be instantianted by a :class:`.ConfigFactory`.

    """
    def __init__(self, msg: str, factory: ConfigFactory = None):
        if factory is not None:
            config = factory.config
            if config is not None and hasattr(config, 'config_file') and \
               isinstance(config.config_file, (str, Path)):
                cf = config.config_file
                if isinstance(cf, Path):
                    cf = cf.absolute()
                msg += f', in file: {cf}'
        super().__init__(msg)


class FactoryState(Enum):
    """The state updated from an instance of :class:`.ConfigFactory`.  Currently
    the only state is that an object has finished being created.

    Future states might inlude when a :class:`.ImportConfigFactory` has created
    all objects from a configuration shared session.

    """
    CREATED = 1


class FactoryStateObserver(ABC):
    """An interface that recieves notifications that the factory has created this
    instance.  This is useful for classes such as :class:`.Writeback`.

    :see: :class:`.Writeback`

    """
    @abstractmethod
    def _notify_state(self, state: FactoryState):
        pass


class FactoryClassImporter(ClassImporter):
    """Just like the super class, but if instances of type
    :class:`.FactoryStateObserver` are notified with a
    :class:`.FactoryState.CREATED`.

    """
    def _bless(self, inst: Any) -> Any:
        if isinstance(inst, FactoryStateObserver):
            inst._notify_state(FactoryState.CREATED)
        return super()._bless(inst)


class ImportClassResolver(ClassResolver):
    """Resolve a class name from a list of registered class names without the
    module part.  This is used with the ``register`` method on
    :class:`.ConfigFactory`.

    :see: :meth:`.ConfigFactory.register`

    """
    def __init__(self, reload: bool = False):
        self.reload = reload

    def create_class_importer(self, class_name: str):
        return FactoryClassImporter(class_name, reload=self.reload)

    def find_class(self, class_name: str):
        class_importer = self.create_class_importer(class_name)
        return class_importer.get_module_class()[1]


class ConfigFactory(object):
    """Creates new instances of classes and configures them given data in a
    configuration :class:`.Configurable` instance.

    """
    NAME_ATTRIBUTE = 'name'
    """The *name* of the parameter given to ``__init__``.  If a parameter of this
    name is on the instance being created it will be set from the name of the
    section.

    """
    CONFIG_ATTRIBUTE = 'config'
    """The *configuration* of the parameter given to ``__init__``.  If a parameter
    of this name is on the instance being created it will be set as the
    instance of the configuration given to the initializer of this factory
    instance.

    """
    CONFIG_FACTORY_ATTRIBUTE = 'config_factory'
    """The *configuration factory* of the parameter given to ``__init__``.  If a
    parameter of this name is on the instance being created it will be set as
    the instance of this configuration factory.

    """
    CLASS_NAME = 'class_name'
    """The class name attribute in the section that identifies the fully qualified
    instance to create.

    """
    def __init__(self, config: Configurable, pattern: str = '{name}',
                 default_name: str = 'default',
                 class_resolver: ClassResolver = None):
        """Initialize a new factory instance.

        :param config: the configuration used to create the instance; all data
                       from the corresponding section is given to the
                       ``__init__`` method
        :param pattern: section pattern used to find the values given to the
                        ``__init__`` method
        :param config_param_name: the ``__init__`` parameter name used for the
                                  configuration object given to the factory's
                                  ``instance`` method; defaults to ``config``
        :param config_param_name: the ``__init__`` parameter name used for the
                                  instance name given to the factory's
                                  ``instance`` method; defaults to ``name``

        """
        self.config = config
        self.pattern = pattern
        self.default_name = default_name
        if class_resolver is None:
            self.class_resolver = DictionaryClassResolver(
                self.INSTANCE_CLASSES)
        else:
            self.class_resolver = class_resolver

    @classmethod
    def register(cls, instance_class: Type, name: str = None):
        """Register a class with the factory.  This method assumes the factory instance
        was created with a (default) :class:`.DictionaryClassResolver`.

        :param instance_class: the class to register with the factory (not a
                               string)

        :param name: the name to use as the key for instance class lookups;
                     defaults to the name of the class

        """
        if name is None:
            name = instance_class.__name__
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'registering: {instance_class} for {cls} -> {name}')
        cls.INSTANCE_CLASSES[name] = instance_class

    def _find_class(self, class_name: str) -> Type:
        """Resolve the class from the name."""
        return self.class_resolver.find_class(class_name)

    def _class_name_params(self, name: str) -> Tuple[str, Dict[str, Any]]:
        """Get the class name and parameters to use to create an instance.

        :param name: the configuration section name, which is the object name

        :return: a tuple of the fully qualified class name and the parameters
                 used as arguments to the class initializer; if a class is not
                 provided it defaults to :class:`.Settings`

        """
        sec = self.pattern.format(**{'name': name})
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'section: {sec}')
        params: Dict[str, Any] = {}
        try:
            params.update(self.config.populate({}, section=sec))
        except Exception as e:
            raise FactoryError(
                f'Can not populate from section {sec}', self) from e
        class_name = params.get(self.CLASS_NAME)
        if class_name is None:
            if len(params) == 0:
                raise FactoryError(f"No such entry: '{name}'", self)
            else:
                class_name = 'zensols.config.Settings'
        else:
            del params[self.CLASS_NAME]
        return class_name, params

    def _has_init_parameter(self, cls: Type, param_name: str):
        args = inspect.signature(cls.__init__)
        return param_name in args.parameters

    def _instance(self, cls_desc: str, cls: Type, *args, **kwargs):
        """Return the instance.

        :param cls_desc: a description of the class (i.e. section name)

        :param cls: the class to create the instance from

        :param args: given to the ``__init__`` method

        :param kwargs: given to the ``__init__`` method

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'args: {args}, kwargs: {kwargs}')
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'config factory creating instance of {cls}')
            inst = cls(*args, **kwargs)
            if isinstance(inst, FactoryStateObserver):
                inst._notify_state(FactoryState.CREATED)
        except Exception as e:
            llen = 200
            kwstr = str(kwargs)
            if len(kwstr) > llen:
                kwstr = 'keys: ' + (', '.join(kwargs.keys()))
            kwstr = textwrap.shorten(kwstr, llen)
            raise FactoryError(f'Can not create \'{cls_desc}\' for class ' +
                               f'{cls}({args})({kwstr}): {e}', self) from e
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'inst: {inst.__class__}')
        return inst

    def instance(self, name: Optional[str] = None, *args, **kwargs):
        """Create a new instance using key ``name``.

        :param name: the name of the class (by default) or the key name of the
                     class used to find the class; this is the section name for
                     the :class:`.ImportConfigFactory`

        :param args: given to the ``__init__`` method

        :param kwargs: given to the ``__init__`` method

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'new instance of {name}')
        t0 = time()
        name = self.default_name if name is None else name
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating instance of {name}')
        class_name, params = self._class_name_params(name)
        if self.CLASS_NAME in kwargs:
            class_name = kwargs.pop(self.CLASS_NAME)
        cls = self._find_class(class_name)
        params.update(kwargs)
        if self._has_init_parameter(cls, self.CONFIG_ATTRIBUTE) \
           and self.CONFIG_ATTRIBUTE not in params:
            logger.debug('setting config parameter')
            params['config'] = self.config
        if self._has_init_parameter(cls, self.NAME_ATTRIBUTE) \
           and self.NAME_ATTRIBUTE not in params:
            logger.debug('setting name parameter')
            params['name'] = name
        if self._has_init_parameter(cls, self.CONFIG_FACTORY_ATTRIBUTE) \
           and self.CONFIG_FACTORY_ATTRIBUTE not in params:
            logger.debug('setting config factory parameter')
            params['config_factory'] = self
        if logger.isEnabledFor(logging.DEBUG):
            for k, v in params.items():
                logger.debug(f'populating {k} -> {v} ({type(v)})')
        inst = self._instance(name, cls, *args, **params)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'created {name} instance of {cls.__name__} ' +
                         f'in {(time() - t0):.2f}s')
        return inst

    def get_class(self, name: str) -> Type:
        """Return a class by name.

        :param name: the name of the class (by default) or the key name of the
                     class used to find the class; this is the section name for
                     the :class:`.ImportConfigFactory`
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'new instance of {name}')
        name = self.default_name if name is None else name
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating instance of {name}')
        class_name, params = self._class_name_params(name)
        return self._find_class(class_name)

    def from_config_string(self, v: str) -> Any:
        """Create an instance from a string used as option values in the configuration.

        """
        try:
            v = eval(v)
        except Exception:
            pass
        return self.instance(v)

    def clone(self) -> Any:
        """Return a copy of this configuration factory that functionally works the
        same.

        """
        return cp.copy(self)

    def __call__(self, *args, **kwargs):
        """Calls ``instance``.

        """
        return self.instance(*args, **kwargs)
