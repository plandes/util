"""Contains general purpose persistence library classes.

"""
__author__ = 'Paul Landes'

from typing import Any, Union, Callable
from abc import ABC
import logging
import traceback
from io import StringIO

logger = logging.getLogger(__name__)


class Deallocatable(ABC):
    """All subclasses have the ability to deallocate any resources.  This is useful
    for cases where there could be reference cycles or deallocation (i.e. CUDA
    tensors) need happen implicitly and faster.

    """
    PRINT_TRACE = False
    ALLOCATION_TRACKING = False
    ALLOCATIONS = {}
    logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()
        if self.ALLOCATION_TRACKING:
            k = id(self)
            sio = StringIO()
            traceback.print_stack(file=sio)
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f'adding allocated key: {k} = {type(self)}')
            self.ALLOCATIONS[k] = (self, sio.getvalue())

    def deallocate(self):
        """Deallocate all resources for this instance.

        """
        k = id(self)
        if self.PRINT_TRACE:
            traceback.print_stack()
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'deallocating {k}: {self.__class__}')
        if self.ALLOCATION_TRACKING:
            if k in self.ALLOCATIONS:
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f'removing allocated key: {k}')
                del self.ALLOCATIONS[k]
            else:
                self.logger.info(f'no key to deallocate: {k} ({type(self)})')

    def _try_deallocate(self, obj: Any):
        cls = globals()['Deallocatable']
        if isinstance(obj, cls):
            obj.deallocate()
            return True
        return False

    @classmethod
    def _print_undeallocated(self, include_stack: bool = False):
        """Print all unallocated objects.

        """
        for k, (v, stack) in self.ALLOCATIONS.items():
            vstr = str(type(v))
            if hasattr(v, 'name'):
                vstr = f'{vstr} ({v.name})'
            print(f'{k} -> {vstr}')
            if include_stack:
                print(stack)


class dealloc(object):
    """Object used with a ``with`` scope for deallocating any subclass of
    :class:`Deallocatable``.  The first argument can also be a function, which
    is useful when tracking deallocations when ``track`` is ``True``.

    Example:
        with dealloc(lambda: ImportClassFactory('some/path')) as fac:
            return fac.instance('stash')

    """
    def __init__(self, inst: Union[Callable, Deallocatable],
                 track: bool = False, include_stack: bool = False):
        """Initialize.

        :param inst: either an object instance to deallocate or a callable that
                     creates the instance to deallocate

        :param track: when ``True``, set
                      :py:attrib:~`.Deallocatable.ALLOCATION_TRACKING` to
                      ``True`` to start tracking allocations

        :param include_stack: adds stack traces in the call to
                              :py:meth:`.Deallocatable._print_undeallocated`

        """
        self.track = track
        self.include_stack = include_stack
        self.org_track = Deallocatable.ALLOCATION_TRACKING
        if track:
            Deallocatable.ALLOCATION_TRACKING = True
        if callable(inst):
            inst = inst()
        self.inst = inst

    def __enter__(self):
        return self.inst

    def __exit__(self, type, value, traceback):
        self.inst.deallocate()
        if self.track:
            Deallocatable._print_undeallocated(self.include_stack)
        Deallocatable.ALLOCATION_TRACKING = self.org_track
