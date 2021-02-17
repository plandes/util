"""A utility class to load classes from modules.

"""
__author__ = 'Paul Landes'

import logging
import importlib
from functools import reduce
import re

logger = logging.getLogger(__name__)


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

    def parse_module_class(self):
        """Parse the module and class name part of the fully qualifed class name.
        """

        cname = self.class_name
        match = re.match(self.CLASS_REGEX, cname)
        if not match:
            raise ValueError(f'not a fully qualified class name: {cname}')
        return match.groups()

    def get_module_class(self):
        """Return the module and class as a tuple of the given class in the
        initializer.

        :param reload: if ``True`` then reload the module before returning the
                       class

        """
        pkg, cname = self.parse_module_class()
        logger.debug(f'pkg: {pkg}, class: {cname}')
        pkg_s = pkg.split('.')
        mod = reduce(lambda m, n: getattr(m, n), pkg_s[1:], __import__(pkg))
        logger.debug(f'mod: {mod}, reloading: {self.reload}')
        if self.reload:
            logger.debug(f'reload: cls: {mod}, {cname}')
            mod = importlib.reload(mod)
        if not hasattr(mod, cname):
            raise ValueError(f"no class '{cname}' found in module '{mod}'")
        cls = getattr(mod, cname)
        logger.debug(f'class: {cls}')
        return mod, cls

    def instance(self, *args, **kwargs):
        """Create an instance of the specified class in the initializer.

        :param args: the arguments given to the initializer of the new class
        :param kwargs: the keyword arguments given to the initializer of the
                     new class

        """
        mod, cls = self.get_module_class()
        try:
            logger.debug(f'class importer creating instance of {cls}')
            inst = cls(*args, **kwargs)
            # if isinstance(inst, FactoryStateObserver):
            #     inst._notify_state(FactoryState.CREATED)
        except Exception as e:
            msg = f'can not instantiate {cls}({args}, {kwargs})'
            logger.error(msg, e)
            raise e
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'inst: {inst}')
        return inst

    def set_log_level(self, level=logging.INFO):
        """Convenciene method to set the log level of the module given in the
        initializer of this class.

        :param level: and instance of ``logging.<level>``
        """
        mod, cls = self.parse_module_class()
        logging.getLogger(mod).setLevel(level)
