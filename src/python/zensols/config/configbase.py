"""Abstract base class for a configuration read from a file.

"""
__author__ = 'Paul Landes'

from abc import ABCMeta, abstractmethod
import logging
from pathlib import Path
import inspect
import pkg_resources
from . import Serializer, Writable

logger = logging.getLogger(__name__)


class Configurable(Writable, metaclass=ABCMeta):
    """An abstract base class that represents an application specific
    configuration.

    """
    def __init__(self, config_file, default_expect):
        self.config_file = config_file
        self.default_expect = default_expect
        self.serializer = Serializer()

    def _narrow_expect(self, expect):
        if expect is None:
            expect = self.default_expect
        return expect

    @abstractmethod
    def get_option(self, name, section=None, vars=None, expect=None):
        """Return an option from ``section`` with ``name``.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        pass

    @abstractmethod
    def get_options(self, section='default', opt_keys=None, vars=None):
        """Get all options for a section.  If ``opt_keys`` is given return only
        options with those keys.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        pass

    @abstractmethod
    def has_option(self, name, section=None):
        pass

    def get_option_list(self, name, section=None, vars=None,
                        expect=None, separator=','):
        """Just like :py:meth:`get_option` but parse as a list using ``split``.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        val = self.get_option(name, section, vars, expect)
        return val.split(separator) if val else []

    def get_option_boolean(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as a boolean (any case `true`).

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        val = self.get_option(name, section, vars, expect)
        val = val.lower() if val else 'false'
        return val == 'true'

    def get_option_int(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as an integer.

        :param section: section in the ini file to fetch the value; defaults to
                        constructor's ``default_section``

        :param vars: contains the defaults for missing values of ``name``

        :param expect: if ``True`` raise an exception if the value does not
                       exist

        """
        val = self.get_option(name, section, vars, expect)
        if val:
            return int(val)

    def get_option_float(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as a float.

        """
        val = self.get_option(name, section, vars, expect)
        if val:
            return float(val)

    def get_option_path(self, name, section=None, vars=None,
                        expect=None, create=None):
        """Just like :py:meth:`get_option` but return a ``pathlib.Path`` object of the
        string.

        :param create: if ``parent`` then create the path and all parents not
                       including the file; if ``dir``, then create all parents;
                       otherwise do not create anything

        """
        val = self.get_option(name, section, vars, expect)
        path = None
        if val is not None:
            path = Path(val)
            if create == 'dir':
                path.mkdir(parents=True, exist_ok=True)
            if create == 'file':
                path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def get_option_object(self, name, section=None, vars=None, expect=None):
        """Just like :py:meth:`get_option` but parse as an object per object syntax
        rules.

        :see: :py:meth:`.parse_object`

        """
        val = self.get_option(name, section, vars, expect)
        if val:
            return self.serializer.parse_object(val)

    @property
    def options(self):
        """Return all options from the default section.

        """
        return self.get_options()

    def populate(self, obj=None, section=None, parse_types=True):
        """Set attributes in ``obj`` with ``setattr`` from the all values in
        ``section``.

        """
        section = self.default_section if section is None else section
        sec = self.get_options(section)
        return self.serializer.populate_state(sec, obj, parse_types)

    def _get_calling_module(self):
        """Get the last module in the call stack that is not this module or ``None`` if
        the call originated from this module.

        """
        for frame in inspect.stack():
            mod = inspect.getmodule(frame[0])
            logger.debug(f'calling module: {mod}')
            if mod is not None:
                mod_name = mod.__name__
                if mod_name != __name__:
                    return mod

    def resource_filename(self, resource_name, module_name=None):
        """Return a resource based on a file name.  This uses the ``pkg_resources``
        package first to find the resources.  If it doesn't find it, it returns
        a path on the file system.

        :param: resource_name the file name of the resource to obtain (or name
                if obtained from an installed module)
        :param module_name: the name of the module to obtain the data, which
                            defaults to ``__name__``
        :return: a path on the file system or resource of the installed module

        """
        if module_name is None:
            mod = self._get_calling_module()
            logger.debug(f'calling module: {mod}')
            if mod is not None:
                mod_name = mod.__name__
        if module_name is None:
            module_name = __name__
        if pkg_resources.resource_exists(mod_name, resource_name):
            res = pkg_resources.resource_filename(mod_name, resource_name)
        else:
            res = resource_name
        return Path(res)