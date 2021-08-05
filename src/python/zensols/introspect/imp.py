"""A utility class to load classes from modules.

"""
__author__ = 'Paul Landes'

from typing import Any, Tuple, Type, Sequence
import logging
import importlib
from functools import reduce
import re

logger = logging.getLogger(__name__)


class ClassImporterError(Exception):
    """Raised for any run time exceptions during resolving and instantiating
    classes with :class:`.ClassImporter`.

    """
    pass


class ClassImporter(object):
    """Utility class that reloads a module and instantiates a class from a string
    class name.  This is handy for prototyping code in a Python REPL.

    """
    CLASS_REGEX = re.compile(r'^(.+)\.(.+?)$')

    def __init__(self, class_name: str, reload: bool = True):
        """Initialize with the class name.

        :param class_name: the fully qualifed name of the class (including the
                           module portion of the class name)
        :param reload: if ``True`` then reload the module before returning the
                       class
        """
        self.class_name = class_name
        self.reload = reload

    @staticmethod
    def full_classname(cls: type) -> str:
        """Return a fully qualified class name string for class ``cls``.

        """
        module = cls.__module__
        if module is None or module == str.__class__.__module__:
            return cls.__name__
        else:
            return module + '.' + cls.__name__

    def parse_module_class(self) -> Sequence[str]:
        """Parse the module and class name part of the fully qualifed class name.
        """

        cname = self.class_name
        match = re.match(self.CLASS_REGEX, cname)
        if not match:
            raise ClassImporterError(
                f'not a fully qualified class name: {cname}')
        return match.groups()

    def get_module_class(self) -> Tuple[Any, Type]:
        """Return the module and class as a tuple of the given class in the
        initializer.

        """
        pkg, cname = self.parse_module_class()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'pkg: {pkg}, class: {cname}')
        pkg_s = pkg.split('.')
        mod = reduce(lambda m, n: getattr(m, n), pkg_s[1:], __import__(pkg))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'mod: {mod}, reloading: {self.reload}')
        if self.reload:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'reload: cls: {mod}, {cname}')
            mod = importlib.reload(mod)
        if not hasattr(mod, cname):
            raise ClassImporterError(
                f"no class '{cname}' found in module '{mod}'")
        cls = getattr(mod, cname)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'class: {cls}')
        return mod, cls

    def get_class(self) -> type:
        """Return the given class in the initializer.

        """
        return self.get_module_class()[1]

    def _bless(self, inst: Any) -> Any:
        """A template method to modify a nascent instance just created.  The returned
        instance is the instance used.

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
            msg = f'can not instantiate {cls}({args}, {kwargs})'
            logger.error(msg, e)
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
