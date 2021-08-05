"""Contains general purpose persistence library classes.

"""
__author__ = 'Paul Landes'

from typing import Any, Union, Callable, Tuple
from abc import ABC
import logging
import collections
import traceback
from io import StringIO
from zensols.util import APIError

logger = logging.getLogger(__name__)


class Deallocatable(ABC):
    """All subclasses have the ability to deallocate any resources.  This is useful
    for cases where there could be reference cycles or deallocation (i.e. CUDA
    tensors) need happen implicitly and faster.

    .. document private functions
    .. automethod:: _print_undeallocated
    .. automethod:: _deallocate_attribute
    .. automethod:: _try_deallocate

    """
    PRINT_TRACE = False
    """When ``True``, print the stack trace when deallocating with
    :meth:`deallocate`.

    """

    ALLOCATION_TRACKING = False
    """Enables allocation tracking.  When this if ``False``, this functionality is
    not used and disabled.

    """

    ALLOCATIONS = {}
    """The data structure that retains all allocated instances.

    """

    # when true, recurse through deallocatable instances while freeing
    _RECURSIVE = False

    def __init__(self):
        super().__init__()
        if self.ALLOCATION_TRACKING:
            k = id(self)
            sio = StringIO()
            traceback.print_stack(file=sio)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'adding allocated key: {k} -> {type(self)}')
            self.ALLOCATIONS[k] = (self, sio.getvalue())

    def deallocate(self):
        """Deallocate all resources for this instance.

        """
        k = id(self)
        if self.PRINT_TRACE:
            traceback.print_stack()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'deallocating {k}: {self._deallocate_str()}')
        self._mark_deallocated(k)

    def _mark_deallocated(self, obj: Any = None):
        """Mark ``obj`` as deallocated regardless if it is, or ever will be
        deallocated.  After this is called, it will not be reported in such
        methods as :meth:`_print_undeallocated`.

        """
        if obj is None:
            k = id(self)
        else:
            k = obj
        if self.ALLOCATION_TRACKING:
            if k in self.ALLOCATIONS:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'removing allocated key: {k}')
                del self.ALLOCATIONS[k]
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'no key to deallocate: {k} ' +
                                 f'({self._deallocate_str()})')

    @staticmethod
    def _try_deallocate(obj: Any, recursive: bool = False) -> bool:
        """If ``obj`` is a candidate for deallocation, deallocate it.

        :param obj: the object instance to deallocate

        :return: ``True`` if the object was deallocated, otherwise return
                 ``False`` indicating it can not and was not deallocated

        """
        cls = globals()['Deallocatable']
        recursive = recursive or cls._RECURSIVE
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'trying to deallocate: {type(obj)}')
        if isinstance(obj, cls):
            obj.deallocate()
            return True
        elif recursive and isinstance(obj, (tuple, list, set)):
            for o in obj:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'deallocate tuple item: {type(o)}')
                cls._try_deallocate(o, recursive)
            return True
        elif recursive and isinstance(obj, dict):
            for o in obj.values():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'deallocate dict item: {type(o)}')
                cls._try_deallocate(o, recursive)
            return True
        return False

    def _deallocate_attribute(self, attrib: str) -> bool:
        """Deallocate attribute ``attrib`` if possible, which means it both exists and
        extends from this class.

        """
        deallocd = False
        if hasattr(self, attrib):
            inst = getattr(self, attrib)
            deallocd = self._try_deallocate(inst)
            if logger.isEnabledFor(logging.DEBUG):
                logging.debug(f'deallocated {type(self)}.{attrib}')
            delattr(self, attrib)
        return deallocd

    def _deallocate_attributes(self, attribs: Tuple[str]) -> int:
        """Deallocates all attributes in ``attribs`` using
        :meth:`_deallocate_attribute`.

        """
        cnt = 0
        for attrib in attribs:
            if self._deallocate_attribute(attrib):
                cnt += 1
        return cnt

    @classmethod
    def _print_undeallocated(cls, include_stack: bool = False,
                             only_counts: bool = False,
                             fail: bool = False):
        """Print all unallocated objects.

        :param include_stack: if ``True`` print out the stack traces of all the
                              unallocated references; if ``only_counts`` is
                              ``True``, this is ignored

        :param only_counts: if ``True`` only print the counts of each
                            unallocated class with counts for each

        :param fail: if ``True``, raise an exception if there are any
                     unallocated references found

        """
        allocs = cls.ALLOCATIONS
        if len(allocs) > 0:
            print(f'total allocations: {len(allocs)}')
        if only_counts:
            cls_counts = collections.defaultdict(lambda: 0)
            for cls in map(lambda o: type(o[0]), allocs.values()):
                cls_counts[cls] += 1
            for k in sorted(cls_counts.keys(), key=lambda x: x.__name__):
                print(f'{k}: {cls_counts[k]}')
        else:
            for k, (v, stack) in allocs.items():
                vstr = str(type(v))
                if hasattr(v, 'name'):
                    vstr = f'{vstr} ({v.name})'
                print(f'{k} -> {vstr}')
                if include_stack:
                    print(stack)
        if fail:
            cls.assert_dealloc()

    @classmethod
    def _deallocate_all(cls):
        """Deallocate all the objects that have not yet been and clear the data
        structure.

        """
        allocs = cls.ALLOCATIONS
        to_dealloc = tuple(allocs.values())
        allocs.clear()
        for obj, trace in to_dealloc:
            obj.deallocate()

    def _deallocate_str(self) -> str:
        return str(self.__class__)

    @classmethod
    def assert_dealloc(cls):
        cnt = len(cls.ALLOCATIONS)
        if cnt > 0:
            raise APIError(f'resource leak with {cnt} intances')


class dealloc_recursive(object):
    def __init__(self):
        self.org_rec_state = Deallocatable._RECURSIVE

    def __enter__(self):
        Deallocatable._RECURSIVE = True

    def __exit__(self, type, value, traceback):
        Deallocatable._RECURSIVE = self.org_rec_state


class dealloc(object):
    """Object used with a ``with`` scope for deallocating any subclass of
    :class:`Deallocatable``.  The first argument can also be a function, which
    is useful when tracking deallocations when ``track`` is ``True``.

    Example::

        with dealloc(lambda: ImportClassFactory('some/path')) as fac:
            return fac.instance('stash')

    """
    def __init__(self, inst: Union[Callable, Deallocatable],
                 track: bool = False, include_stack: bool = False):
        """
        :param inst: either an object instance to deallocate or a callable that
                     creates the instance to deallocate

        :param track: when ``True``, set
                      :obj:`.Deallocatable.ALLOCATION_TRACKING` to ``True`` to
                      start tracking allocations

        :param include_stack: adds stack traces in the call to
                              :meth:`.Deallocatable._print_undeallocated`

        """
        self.track = track
        self.include_stack = include_stack
        self.org_track = Deallocatable.ALLOCATION_TRACKING
        if track:
            Deallocatable.ALLOCATION_TRACKING = True
        if callable(inst) and not isinstance(inst, Deallocatable):
            inst = inst()
        self.inst = inst

    def __enter__(self):
        return self.inst

    def __exit__(self, type, value, traceback):
        self.inst.deallocate()
        if self.track:
            Deallocatable._print_undeallocated(self.include_stack)
        Deallocatable.ALLOCATION_TRACKING = self.org_track
