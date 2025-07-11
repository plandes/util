"""Contains general purpose persistence library classes.

"""
__author__ = 'Paul Landes'

from typing import Union, Any, Dict, Type, Tuple, ClassVar
import logging
import sys
import re
from copy import copy
import pickle
import string
import time as tm
from datetime import datetime
import os
from pathlib import Path
from zensols.util import APIError
import zensols.util.time as time
from . import Deallocatable

logger = logging.getLogger(__name__)


class PersistableError(APIError):
    """Thrown for any persistable API error"""
    pass


class FileTextUtil(object):
    """Basic file naming utility methods.

    """
    _NORMALIZE_REGEX: ClassVar[re.Pattern] = re.compile(
        r"""[ \t\n\\\[\]()\/()<>{}:;_`'"|!@#$%^&*~?!,+=.-]+""")
    """The default regular expression for :meth:`normalize_text`."""

    @classmethod
    def normalize_text(cls: Type, name: str, replace_char: str = '-',
                       lower: bool = True, regex: re.Pattern = None,
                       remove_non_printable: bool = False) -> str:
        """Normalize the name in to a string that is more file system friendly.
        This removes special characters and replaces them with ``replace_char``.

        :param name: the name to be normalized

        :param replace_char: the character used to replace special characters

        :param lower: whether to lowercase the text

        :param regex: the regular expression that matches on text to remove

        :param remove_non_printable: whether to keep only ASCII characters

        :return: the normalized name

        """
        if lower:
            name = name.lower()
        regex = cls._NORMALIZE_REGEX if regex is None else regex
        name = re.sub(regex, replace_char, name)
        # remove beginning and trailing dashes
        nlen = len(name)
        if nlen > 1:
            if name[0] == replace_char:
                name = name[1:]
            if nlen > 2 and name[-1] == replace_char:
                name = name[:-1]
        if remove_non_printable:
            printable = set(string.printable)
            name = ''.join(filter(lambda x: x in printable, name))
        return name

    @classmethod
    def normalize_path(cls: Type, path: Path, replace_char: str = '-',
                       lower: bool = True, regex: re.Pattern = None,
                       remove_non_printable: bool = False) -> Path:
        """Applies :meth:`normalize_text` for each component of the path and
        return it.  Directory separators and tilde (``~``) are not normalized.

        :see: :meth:`normalize_text`

        """
        def map_part(s: str) -> str:
            norm: str = s
            if s != os.sep and s != '~':
                norm = cls.normalize_text(
                    s, replace_char, lower, regex, remove_non_printable)
            return norm

        return Path(*tuple(map(map_part, path.parts)))

    @staticmethod
    def byte_format(num: int, suffix: str = 'B') -> str:
        """Return a human readable string of the number of bytes ``num``.

        :param num: the number of bytes to format

        :param suffix: the suffix to append to the resulting string

        :attribution: `Fred Cirera <https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size>`

        """
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return f'{num:3.1f}{unit}{suffix}'
            num /= 1024.0
        return f'{num:.1f}Yi{suffix}'

    @staticmethod
    def unique_tracked_name(prefix: str, include_user: bool = True,
                            include_time: bool = True,
                            extension: str = None) -> str:
        """Create a unique file name useful for tracking files.

        :param prefix: the file name that identifier

        :param include_user: whether to add the user name in the file

        """
        time: str = ''
        user: str = ''
        if include_time:
            time = '-' + datetime.now().strftime('%b%d-%H%M')
        if include_user:
            user = os.environ['USER'] if 'USER' in os.environ else os.getlogin()
            user = f'-{user}'
        if extension is None:
            extension = ''
        else:
            extension = f'.{extension}'
        return f'{prefix}{user}{time}{extension}'.lower()


# class level persistance
class PersistedWork(Deallocatable):
    """This class caches data in the instance of the contained class and/or
    global level.  In addition, the data is also pickled to disk to avoid any
    expensive recomputation of the data.

    In order, it first looks for the data in ``owner``, then in globals (if
    ``cache_global`` is True), then it looks for the data on the file system.
    If it can't find it after all of this it invokes function ``worker`` to
    create the data and then pickles it to the disk.

    This class is a callable itself, which is invoked to get or create the
    work.

    There are two ways to implement the data/work creation: pass a ``worker``
    to the ``__init__`` method or extend this class and override
    ``__do_work__``.

    """
    def __init__(self, path: Union[str, Path], owner: object,
                 cache_global: bool = False, transient: bool = False,
                 initial_value: Any = None, mkdir: bool = False,
                 deallocate_recursive: bool = False,
                 recover_empty: bool = False):
        """Create an instance of the class.

        :param path: if type of :class:`pathlib.Path` then use disk storage to
                     cache of the pickeled data, otherwise a string used to
                     store in the owner

        :param owner: an owning class to get and retrieve as an attribute

        :param cache_global: cache the data globals; this shares data across
                             instances but not classes

        :param transient: the data not persisted to disk after invoking the
                          method

        :param initial_value: if provided, the method is never called and this
                              value returned for all invocations

        :param mkdir: if ``path`` is a :class`pathlib.Path` object, then
                      recursively create all directories needed to be able to
                      persist the file without missing directory IO errors

        :deallocate_recursive: the ``recursive`` parameter passed to
                               :meth:`.Deallocatable._try_deallocate` to try to
                               deallocate the object graph recursively

        :param recover_empty: if ``True`` and a ``path`` points to a zero size
                              file, treat it as data that has not yet been
                              generated; this is useful when a previous
                              exception was raised leaving a zero byte file

        """
        super().__init__()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'pw inst: path={path}, global={cache_global}')
        self.owner = owner
        self.cache_global = cache_global
        self.transient = transient
        self.worker = None
        if isinstance(path, Path):
            self.path = path
            self.use_disk = True
            fname = FileTextUtil.normalize_text(str(self.path.absolute()), '_')
        else:
            self.path = Path(path)
            self.use_disk = False
            fname = str(path)
        cstr = owner.__module__ + '.' + owner.__class__.__name__
        self.varname = f'_{cstr}_{fname}_pwvinst'
        if initial_value is not None:
            self.set(initial_value)
        self.mkdir = mkdir
        self.deallocate_recursive = deallocate_recursive
        self.recover_empty = recover_empty

    def _info(self, msg, *args):
        if logger.isEnabledFor(logging.INFO):
            logger.info(self.varname + ': ' + msg, *args)

    def clear_global(self):
        """Clear only any cached global data.

        """
        vname = self.varname
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'global clearing {vname}')
        if vname in globals():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('removing global instance var: {}'.format(vname))
            del globals()[vname]

    def clear(self):
        """Clear the data, and thus, force it to be created on the next fetch.
        This is done by removing the attribute from ``owner``, deleting it from
        globals and removing the file from the disk.

        """
        vname = self.varname
        if self.use_disk and self.path.is_file():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('deleting cached work: {}'.format(self.path))
            self.path.unlink()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'owner exists: {self.owner is not None} ' +
                         f'has {vname}: {hasattr(self.owner, vname)}')
        if self.owner is not None and hasattr(self.owner, vname):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('removing instance var: {}'.format(vname))
            delattr(self.owner, vname)
        self.clear_global()

    def deallocate(self):
        super().deallocate()
        vname = self.varname
        if self.owner is not None and hasattr(self.owner, vname):
            obj = getattr(self.owner, vname)
            self._try_deallocate(obj, self.deallocate_recursive)
            delattr(self.owner, vname)
        self.clear_global()
        self.owner = None

    def _do_work(self, *argv, **kwargs):
        t0: float = tm.time()
        obj: Any = self.__do_work__(*argv, **kwargs)
        if logger.isEnabledFor(logging.INFO):
            self._info('created work in {:2f}s, saving to {}'.format(
                (tm.time() - t0), self.path))
        return obj

    def _load_or_create(self, *argv, **kwargs):
        """Invoke the file system operations to get the data, or create work.

        If the file does not exist, calling ``__do_work__`` and save it.
        """
        load_file: bool = self.path.is_file()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{self.varname}: load_file: {load_file}')
        if load_file and self.recover_empty and self.path.stat().st_size == 0:
            load_file = False
        if load_file:
            if logger.isEnabledFor(logging.INFO):
                self._info(f'loading work from {self.path}')
            with open(self.path, 'rb') as f:
                try:
                    obj = pickle.load(f)
                except EOFError as e:
                    raise PersistableError(f'Can not read: {self.path}') from e
        else:
            if logger.isEnabledFor(logging.INFO):
                self._info(f'saving work to {self.path}')
            if self.mkdir:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.parent.is_dir():
                raise PersistableError(
                    f'Parent directory does not exist: {self.path.parent}')
            with open(self.path, 'wb') as f:
                obj = self._do_work(*argv, **kwargs)
                pickle.dump(obj, f)
            if logger.isEnabledFor(logging.INFO):
                self._info(f'wrote: {self.path}')
        return obj

    def set(self, obj):
        """Set the contents of the object on the owner as if it were persisted
        from the source.  If this is a global cached instance, then add it to
        global memory.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'saving in memory value {type(obj)}')
        vname = self.varname
        if self.owner is None:
            raise PersistableError(
                f'Owner is not set for persistable: {vname}')
        setattr(self.owner, vname, obj)
        if self.cache_global:
            if vname not in globals():
                globals()[vname] = obj

    def is_set(self) -> bool:
        """Return whether or not the persisted work has been engaged and has
        data.

        """
        vname = self.varname
        if self.cache_global:
            return vname in globals()
        else:
            return self.owner is not None and hasattr(self.owner, vname)

    def __getstate__(self) -> Dict[str, Any]:
        """We must null out the owner and worker as they are not pickelable.

        :see: :class:`.PersistableContainer`

        """
        d = copy(self.__dict__)
        d['owner'] = None
        d['worker'] = None
        return d

    def __call__(self, *argv, **kwargs):
        """Return the cached data if it doesn't yet exist.  If it doesn't exist,
        create it and cache it on the file system, optionally ``owner`` and
        optionally the globals.

        """
        vname = self.varname
        obj = None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{vname}: call')
        if self.owner is not None and hasattr(self.owner, vname):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('found in instance')
            obj = getattr(self.owner, vname)
        if obj is None and self.cache_global:
            if vname in globals():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('found in globals')
                obj = globals()[vname]
        if obj is None:
            if self.use_disk:
                obj = self._load_or_create(*argv, **kwargs)
            else:
                self._info('invoking worker')
                obj = self._do_work(*argv, **kwargs)
        self.set(obj)
        return obj

    def __do_work__(self, *argv, **kwargs):
        """You can extend this class and overriding this method.  This method
        will invoke the worker to do the work.

        """
        if logger.isEnabledFor(logging.INFO):
            self._info(f'do work: {self.worker}')
        res = self.worker(*argv, **kwargs)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{self.varname}: work result: {type(res)}')
        return res

    def write(self, indent=0, include_content=False, writer=sys.stdout):
        sp = ' ' * indent
        writer.write(f'{sp}{self}:\n')
        sp = ' ' * (indent + 1)
        writer.write(f'{sp}global: {self.cache_global}\n')
        writer.write(f'{sp}transient: {self.transient}\n')
        writer.write(f'{sp}type: {type(self())}\n')
        if include_content:
            writer.write(f'{sp}content: {self()}\n')

    def _deallocate_str(self) -> str:
        return f'{self.varname} => {type(self.owner)}'

    def __str__(self):
        return self.varname

    def __repr__(self):
        return self.__str__()


class PersistableContainerMetadata(object):
    """Provides metadata about :class:`.PersistedWork` definitions in the class.

    """
    def __init__(self, container):
        super().__init__()
        self.container = container

    @property
    def persisted(self):
        """Return all ``PersistedWork`` instances on this object as a ``dict``.

        """
        pws = {}
        for k, v in self.container.__dict__.items():
            if isinstance(v, PersistedWork):
                pws[k] = v
        return pws

    def write(self, indent=0, include_content=False,
              recursive=False, writer=sys.stdout):
        sp = ' ' * indent
        spe = ' ' * (indent + 1)
        for k, v in self.container.__dict__.items():
            if isinstance(v, PersistedWork):
                v.write(indent, include_content, writer=writer)
            else:
                writer.write(f'{sp}{k}:\n')
                writer.write(f'{spe}type: {type(v)}\n')
                if include_content:
                    writer.write(f'{spe}content: {v}\n')
            if recursive and isinstance(v, PersistableContainer):
                cmeta = v._get_persistable_metadata()
                cmeta.write(writer, indent + 2, include_content, True)

    def clear(self):
        """Clear all ``PersistedWork`` instances on this object.

        """
        for pw in self.persisted.values():
            pw.clear()


class PersistableContainer(Deallocatable):
    """Classes can extend this that want to persist :class:`.PersistedWork`
    instances, which otherwise are not persistable.

    This class also manages the deallocation of all :class:`.PersistedWork`
    attributes of the class, which might be another reason to use it even if
    there isn't a persistence use case.

    If the class level attribute ``_PERSITABLE_TRANSIENT_ATTRIBUTES`` is set,
    all attributes given in this set will be set to ``None`` when pickled.

    If the class level attribute ``_PERSITABLE_REMOVE_ATTRIBUTES`` is set, all
    attributes given in this set will be set object deleted when pickled.

    If the class level attribute ``_PERSITABLE_PROPERTIES`` is set, all
    properties given will be accessed for force creation before pickling.

    If the class level attribute ``_PERSITABLE_METHODS`` is set, all method
    given will be accessed for force creation before pickling.

    .. document private functions
    .. automethod:: _clear_persistable_state

    """
    def __getstate__(self) -> Dict[str, Any]:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'get state for {self.__class__}')
        removes = set()
        tran_attribute_name = '_PERSITABLE_TRANSIENT_ATTRIBUTES'
        remove_attribute_name = '_PERSITABLE_REMOVE_ATTRIBUTES'
        prop_attribute_name = '_PERSITABLE_PROPERTIES'
        meth_attribute_name = '_PERSITABLE_METHODS'
        if hasattr(self, prop_attribute_name):
            for attr in getattr(self, prop_attribute_name):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'for property get: {attr}')
                getattr(self, attr)
        if hasattr(self, meth_attribute_name):
            for attr in getattr(self, meth_attribute_name):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'for method get: {attr}')
                getattr(self, attr)()
        state = copy(self.__dict__)
        if hasattr(self, tran_attribute_name):
            tran_attribs = getattr(self, tran_attribute_name)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'transient attributes: {tran_attribs}')
            removes.update(tran_attribs)
        for k, v in state.items():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'container get state: {k} => {type(v)}')
            if isinstance(v, PersistedWork):
                if v.transient:
                    removes.add(v.varname)
        for k in removes:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'removed persistable attribute: {k}')
            state[k] = None
        if hasattr(self, remove_attribute_name):
            remove_attribs = getattr(self, remove_attribute_name)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'remove attributes: {tran_attribs}')
            for k in remove_attribs:
                del state[k]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'state keys for {self.__class__}: ' +
                         f'{", ".join(state.keys())}')
        return state

    def _clear_persistable_state(self):
        """Clear all cached state from all :class:`.PersistedWork` in this
        instance.

        """
        pws: Tuple[PersistedWork, ...] = tuple(filter(
            lambda v: isinstance(v, PersistedWork),
            self.__dict__.values()))
        for v in pws:
            v.clear()

    def __setstate__(self, state: Dict[str, Any]):
        """Set the owner to containing instance and the worker function to the
        owner's function by name.

        """
        self.__dict__.update(state)
        for k, v in state.items():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'container set state: {k} => {type(v)}')
            if isinstance(v, PersistedWork):
                setattr(v, 'owner', self)

    def _get_persistable_metadata(self) -> PersistableContainerMetadata:
        """Return the metadata for this container.

        """
        return PersistableContainerMetadata(self)

    def deallocate(self):
        super().deallocate()
        for pw in self._get_persistable_metadata().persisted.values():
            pw.deallocate()


class persisted(object):
    """Class level annotation to further simplify usage with
    :class:`.PersistedWork`.

    :see: :class:`.PersistedWork`

    For example::

        class SomeClass(object):
            @property
            @persisted('_counter', 'tmp.dat')
            def counter(self):
                return tuple(range(5))

    """
    def __init__(self, name: str, path: Path = None,
                 cache_global: bool = False, transient: bool = False,
                 allocation_track: bool = True, mkdir: bool = False,
                 deallocate_recursive: bool = False,
                 recover_empty: bool = False):
        """Initialize.

        :param name: the name of the attribute on the instance to set with the
                     cached result of the method

        :param: path: if set, the path where to store the cached result on the
                      file system

        :param cache_global: if ``True``, globally cache the value at the class
                             definition level

        :param transient: if ``True`` do not persist only in memory, and not on
                          the file system, which is needed when used with
                          :class:`.PersistableContainer`

        :param allocation_track: if ``False``, immediately mark the backing
                                 :class:`PersistedWork` as deallocated

        :param mkdir: if ``path`` is a :class`.Path` object, then recursively
                      create all directories needed to be able to persist the
                      file without missing directory IO errors

        :deallocate_recursive: the ``recursive`` parameter passed to
                               :meth:`.Deallocate._try_deallocate` to try to
                               deallocate the object graph recursively

        :param recover_empty: if ``True`` and a ``path`` points to a zero size
                              file, treat it as data that has not yet been
                              generated; this is useful when a previous
                              exception was raised leaving a zero byte file

        """
        super().__init__()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'persisted decorator on attr: {name}, ' +
                         f'global={cache_global}')
        self.attr_name = name
        self.path = path
        self.cache_global = cache_global
        self.transient = transient
        self.allocation_track = allocation_track
        self.mkdir = mkdir
        self.deallocate_recursive = deallocate_recursive
        self.recover_empty = recover_empty

    def __call__(self, fn):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'call: {fn}:{self.attr_name}:{self.path}:' +
                         f'{self.cache_global}')

        def wrapped(*argv, **kwargs):
            inst = argv[0]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'wrap: {fn}:{self.attr_name}:{self.path}:' +
                             f'{self.cache_global}')
            pwork: PersistedWork
            if hasattr(inst, self.attr_name):
                pwork = getattr(inst, self.attr_name)
            else:
                if self.path is None:
                    path = self.attr_name
                else:
                    path = Path(self.path)
                pwork = PersistedWork(
                    path, owner=inst, cache_global=self.cache_global,
                    transient=self.transient,
                    mkdir=self.mkdir,
                    deallocate_recursive=self.deallocate_recursive,
                    recover_empty=self.recover_empty)
                setattr(inst, self.attr_name, pwork)
                if not self.allocation_track:
                    pwork._mark_deallocated()
            if pwork is None:
                raise PersistableError(
                    f'PersistedWork not found: {self.attr_name}')
            pwork.worker = fn
            return pwork(*argv, **kwargs)

        # copy documentation over for Sphinx docs
        wrapped.__doc__ = fn.__doc__
        # copy annotations (i.e. type hints) over for Sphinx docs
        wrapped.__annotations__ = fn.__annotations__

        return wrapped


# resource/sql
class resource(object):
    """This annotation uses a template pattern to (de)allocate resources.  For
    example, you can declare class methods to create database connections and
    then close them.  This example looks like this:

    For example::

        class CrudManager(object):
            def _create_connection(self):
                return sqlite3.connect(':memory:')

            def _dispose_connection(self, conn):
                conn.close()

            @resource('_create_connection', '_dispose_connection')
            def commit_work(self, conn, obj):
                conn.execute(...)

    """
    def __init__(self, create_method_name, destroy_method_name):
        """Create the instance based annotation.

        :param create_method_name: the name of the method that allocates
        :param destroy_method_name: the name of the method that deallocates
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'connection decorator {create_method_name} ' +
                         f'destructor method name: {destroy_method_name}')
        self.create_method_name = create_method_name
        self.destroy_method_name = destroy_method_name

    def __call__(self, fn):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'connection call with fn: {fn}')

        def wrapped(*argv, **kwargs):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'in wrapped {self.create_method_name}')
            inst = argv[0]
            resource = getattr(inst, self.create_method_name)()
            try:
                result = fn(inst, resource, *argv[1:], **kwargs)
            finally:
                getattr(inst, self.destroy_method_name)(resource)
            return result

        # copy documentation over for Sphinx docs
        wrapped.__doc__ = fn.__doc__
        # copy annotations (i.e. type hints) over for Sphinx docs
        wrapped.__annotations__ = fn.__annotations__

        return wrapped
