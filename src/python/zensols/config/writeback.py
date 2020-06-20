"""Observer pattern that write updates back to the configuration.

"""
__author__ = 'Paul Landes'

from typing import Set, Any
from dataclasses import dataclass, field
import logging
from zensols.config import (
    ClassResolver,
    ConfigFactory,
    FactoryState,
    FactoryStateObserver,
)

logger = logging.getLogger(__name__)


@dataclass
class Writeback(FactoryStateObserver):
    """Subclass for classes that want to write attribute changes back to a
    :class:`.Configurable`.  This uses an observer pattern that write updates
    back to the configuration.

    When an attribute is set on an instance of this class, it is first set
    using the normal Python attribute setting.  After that, based on a set of
    criteria, the attribute and value are set on the backing configuration
    ``config``.  The value is clobbered with a string version based on the
    ``config``'s :class:`.Serializer` instance (either a primitive value string
    or JSON string).

    **Implementation Note:** During initialization, the :py:meth:`__setattr__`
    is called by the Python interpreter, and before the instance is completely
    being populated.

    **Important:** The :py:meth:`_is_settable` implementation checks for a
    state (any such as ``CREATED``) to be set on the instance.  To change
    this behavior, you will need to overide this method.

    :param name: the name of the section given in the configuration

    :param config: the *backing configuration*, which is the configuration from
                   whince this object instance was defined

    """
    DEFAULT_SKIP_ATTRIBUTES = set([ConfigFactory.NAME_ATTRIBUTE,
                                   ConfigFactory.CONFIG_ATTRIBUTE,
                                   ConfigFactory.CONIFG_FACTORY_ATTRIBUTE])
    name: str
    config_factory: ConfigFactory = field(repr=False)

    def _notify_state(self, state: FactoryState):
        """Called to update the object of a new state.  This is currently only called
        by instances of :class:`.ConfigFactory`.

        This is useful when overridding :py:meth:`is_settable` to disallow
        setting of the configuraiton while the object is being initialized (see
        class docs).

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'notify state: {state}')
        self._state = state

    def _is_created(self) -> bool:
        return hasattr(self, '_state')

    def _get_skip_attributes(self) -> Set[str]:
        """Return a set of attributes to not update based on attribute name.

        """
        return self.DEFAULT_SKIP_ATTRIBUTES

    def _get_keep_attribute(self) -> Set[str]:
        """Return a list of attribute names to allow update.  This is an exclusive
        list, so those not in this set are not updated.  If ``None``, always
        update all.

        """
        return None

    def _is_allowed_type(self, value: Any) -> bool:
        """Return whether or not to allow updating of the type of value.  This
        implementation is delegated to the :class:`Serializer` instance in the
        backing ``config``.

        """
        return self.config_factory.config.serializer.is_allowed_type(value)

    def _allow_config_adds(self) -> bool:
        """Whether or not to allow new entries to be made in the configuration if they
        do not already exist.

        """
        return False

    def _is_settable(self, name: str, value: Any) -> bool:
        """Return whether or not to allow setting attribute ``name`` with ``value`` on
        the current instance.  This also checks to make sure this instance has
        completed initialization by check for the existance of the
        :py:attrib:~`_state` attribute set in :py:meth:`_notify_state`.

        :param name: the name of the attribute

        :param value: the Python object value to be set on the configuration

        """
        keeps = self._get_keep_attribute()
        is_created = self._is_created()
        is_skip = keeps is None or name in keeps
        is_skip = is_skip and name in self._get_skip_attributes()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{name}: is created: {is_created}, skip: {is_skip}')
        return is_created and not is_skip and self._is_allowed_type(value)

    def _set_option(self, name: str, value: Any):
        """Called by :py:meth:`__setattr__` to set the value on the backing ``config``.
        The backing ``config`` handles the string serialization.

        :param name: the name of the attribute

        :param value: the Python object value to be set on the configuration

        """
        config = self.config_factory.config
        has_option = config.has_option(name, section=self.name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'set option {self.name}:{name} ' +
                         f'{value}: {has_option}')
        if self._allow_config_adds() or has_option:
            config.set_option(name, value, section=self.name)

    def _attribute_to_object(self, name: Any, value: Any) -> Any:
        svalue = value
        obj = value
        is_created = self._is_created()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'attrib to obj: {name}: is created: ' +
                         f'{is_created}: {value}')
        if is_created and isinstance(value, str):
            factory = self.config_factory
            config = factory.config
            svalue = config.serializer.parse_object(value)
            obj = factory.from_config_string(svalue)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'attrib to obj: {name}: {value} -> <{obj}>')
        return svalue, obj

    def __setattr__(self, name: str, value: Any):
        """Set an attribute, which is overloaded from the ``builtin object``.

        """
        value, obj = self._attribute_to_object(name, value)
        try:
            super().__setattr__(name, obj)
        except AttributeError as e:
            raise AttributeError(
                f'can\'t set attribute \'{name}\' = {value.__class__}: {e}')
        if self._is_settable(name, value):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'settings option {name} = {value}')
            self._set_option(name, value)

    def asdict(self, class_name_param: str = None):
        wcls = globals()['Writeback']
        ret = {}
        if class_name_param is not None:
            cls = self.__class__
            ret[class_name_param] = ClassResolver.full_classname(cls)
        for k, v in self.__dict__.items():
            if isinstance(v, wcls):
                ret[k] = v.asdict()
            elif self._is_allowed_type(v):
                ret[k] = v
        return ret