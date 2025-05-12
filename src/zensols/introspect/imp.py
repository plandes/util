"""A utility class to load classes from modules.

"""
__author__ = 'Paul Landes'

from typing import Any, Tuple, Type, Sequence, Dict, ClassVar
from types import ModuleType
from abc import ABC
import logging
import importlib
from functools import reduce
import textwrap
import re

logger = logging.getLogger(__name__)


class ClassImporterError(Exception):
    """Raised for any run time exceptions during resolving and instantiating
    classes with :class:`.ClassImporter`.

    """
    pass


class ClassImporter(object):
    """Utility class that reloads a module and instantiates a class from a
    string class name.  This is handy for prototyping code in a Python REPL.

    """
    _CLASS_REGEX: ClassVar[re.Pattern] = re.compile(
        r'^([a-zA-Z0-9_.]+)\.([a-zA-Z_][a-zA-Z0-9_]*)$')

    def __init__(self, class_name: str, reload: bool = True):
        """Initialize with the class name.

        :param class_name: the fully qualifed name of the class (including the
                           module portion of the class name)
        :param reload: if ``True`` then reload the module before returning the
                       class
        """
        self.class_name = class_name
        self.reload = reload

    @classmethod
    def is_valid_class_name(cls: Type, class_name: str) -> bool:
        """Return whether a string represents a valid class name."""
        return cls._CLASS_REGEX.match(class_name) is not None

    @staticmethod
    def full_classname(cls: Type) -> str:
        """Return a fully qualified class name string for class ``cls``.

        """
        module = cls.__module__
        if module is None or module == str.__class__.__module__:
            return cls.__name__
        else:
            return module + '.' + cls.__name__

    @staticmethod
    def get_module(name: str, reload: bool = False) -> ModuleType:
        """Return the module that has ``name``.

        :param name: the string name, which can have dots (``.``) to for sub
                     modules

        """
        pkg_s = name.split('.')
        mod = reduce(lambda m, n: getattr(m, n), pkg_s[1:], __import__(name))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'mod: {mod}, reloading: {reload}')
        if reload:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'reload: cls: {mod}')
            mod = importlib.reload(mod)
        return mod

    def parse_module_class(self) -> Sequence[str]:
        """Parse the module and class name part of the fully qualifed class
        name.

        """

        cname: str = self.class_name
        match: re.Match = re.match(self._CLASS_REGEX, cname)
        if not match:
            raise ClassImporterError(
                f'Not a fully qualified class name: {cname}')
        return match.groups()

    def get_module_class(self, resolve_module: bool = False) -> \
            Tuple[ModuleType, Type]:
        """Return the module and class as a tuple of the given class in the
        initializer.

        :param resolve_module: if ``True`` then resolve the module from the
                               class rather than the module portion of the
                               :obj:`class_name` string

        :return: a tuple of the module and class represented by
                 :obj:`class_name`

        """
        mod_name, cname = self.parse_module_class()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'mod_name: {mod_name}, class: {cname}')
        mod = self.get_module(mod_name, self.reload)
        if not hasattr(mod, cname):
            raise ClassImporterError(
                f"No class '{cname}' found in module '{mod}'")
        cls = getattr(mod, cname)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'class: {cls}')
        if resolve_module:
            mod = self.get_module(cls.__module__, self.reload)
        return mod, cls

    def get_class(self) -> Type:
        """Return the given class in the initializer.

        """
        return self.get_module_class()[1]

    def get_class_or_global(self) -> Type:
        """Like :meth:`get_class` but try globals if the class isn't fully
        qualified (i.e. sans module).

        """
        if self.is_valid_class_name(self.class_name):
            return self.get_class()
        else:
            cls = globals().get(self.class_name)
            if cls is None:
                raise ClassImporterError(
                    'Not a fully qualified class name and not in globals: ' +
                    self.class_name)
            return cls

    def _bless(self, inst: Any) -> Any:
        """A template method to modify a nascent instance just created.  The
        returned instance is the instance used.

        This base class implementation just returns ``inst``.

        :param inst: the instance to bless

        :return: the instance to returned and used by the client

        """
        return inst

    def instance(self, *args, **kwargs):
        """Create an instance of the specified class in the initializer.

        :param args: the arguments given to the initializer of the new class
        :param kwargs: the keyword arguments given to the initializer of the
                     new class

        """
        cls = self.get_class()
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'class importer creating instance of {cls}')
            inst = cls(*args, **kwargs)
            inst = self._bless(inst)
        except Exception as e:
            llen = 200
            kwstr = textwrap.shorten(f'{args}, {kwargs}', llen)
            msg = f'Can not instantiate {cls}({kwstr})'
            logger.error(msg)
            raise e
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'inst class: {type(inst)}')
        return inst

    def set_log_level(self, level: int = logging.INFO):
        """Convenciene method to set the log level of the module given in the
        initializer of this class.

        :param level: a logging level in :mod:`logging`

        """
        mod, cls = self.parse_module_class()
        logging.getLogger(mod).setLevel(level)


class ClassResolver(ABC):
    """Used to resolve a class from a string.

    """
    @staticmethod
    def full_classname(cls: type) -> str:
        """Return a fully qualified class name string for class ``cls``.

        """
        return ClassImporter.full_classname(cls)

    def find_class(self, class_name: str) -> Type:
        """Return a class given the name of the class.

        :param class_name: represents the class name, which might or might not
                           have the module as part of that name

        """
        pass


class DictionaryClassResolver(ClassResolver):
    """Resolve a class name from a list of registered class names without the
    module part.  This is used with the ``register`` method on
    ``ConfigFactory``.

    :see: ConfigFactory.register

    """
    def __init__(self, instance_classes: Dict[str, type]):
        self.instance_classes = instance_classes

    def find_class(self, class_name: str) -> Type:
        classes = {}
        classes.update(globals())
        classes.update(self.instance_classes)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'looking up class: {class_name}')
        if class_name not in classes:
            raise ClassImporterError(
                f'Class {class_name} is not registered in factory {self}')
        cls = classes[class_name]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'found class: {cls}')
        return cls
