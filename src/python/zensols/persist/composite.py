"""Stash implementations.

"""
__author__ = 'Paul Landes'

import logging
from typing import Any, Set, Tuple
from functools import reduce
import collections
import shutil
from pathlib import Path
from . import PersistableError, DirectoryStash

logger = logging.getLogger(__name__)


class MissingDataKeys(PersistableError):
    def __init__(self, keys: Set[str]):
        super().__init__(f'missing data keys: {keys}')
        self.keys = keys


class DirectoryCompositeStash(DirectoryStash):
    """A stash distributes the data of each item out over several directories.  On
    dumping, an attribute holding a ``dict`` is removed from the item, it's
    data is persisted over multiple directories, then the attribute is restored
    after pickling.

    The data is split up amoung groups of keys in the attribute ``dict`` of the
    item.  Persistence works similar to the parent :class:`DirectoryStash`,
    except the path points a directory that has an instance of each item
    without the attribute (called the item instance directory), and the split
    data (called the composite data directory).

    The composite data is grouped across keys from the composite attribute.
    When the data is loaded, if no ``load_keys`` are requested from a group,
    the data is not accessed.  In this way, loading data becomes *much* faster
    for very large objects (i.e. matrix/tensor) data.

    For this reason, it is important to properly group your load keys so the
    most related data goes together.  This is because if only one key is from
    the data is needed, the entire composite item is loaded.

    *Note:* If order of the data is important, use an instance of
     :class:`collections.OrderedDict` as the attribute data.

    """
    INSTANCE_DIRECTORY_NAME = 'inst'
    COMPOSITE_DIRECTORY_NAME = 'comp'

    def __init__(self, path: Path, groups: Tuple[Set[str]],
                 attribute_name: str, load_keys: Set[str] = None):
        """Initialize using the parent class's default pattern.

        :param path: the directory that will have to subdirectories with the
                     files, they are named :obj:`INSTANCE_DIRECTORY_NAME` and
                     :obj:`COMPOSITE_DIRECTORY_NAME`

        :param groups: the groups of the ``dict`` composite attribute, which
                        are sets of keys, each of which are persisted to their
                        respective directory

        :param attribute_name: the name of the attribute in each item to split
                               across groups/directories; the instance data to
                               persist has the composite attribute of type
                               ``dict``


        :param load_keys: the keys used to load the data from the composite
                          stashs in to the attribute ``dict`` instance; only
                          these keys will exist in the loaded data, or ``None``
                          for all keys; this can be set after the creation of
                          the instance as well

        """
        super().__init__(path)
        stashes = {}
        comp_path = self.path / self.COMPOSITE_DIRECTORY_NAME
        self.top_level_dir = self.path
        self.stash_by_group = {}
        self.stash_by_attribute = stashes
        self.path = self.path / self.INSTANCE_DIRECTORY_NAME
        self.groups = groups
        self.all_keys = reduce(lambda a, b: a | b, groups)
        self.load_keys = load_keys
        self.attribute_name = attribute_name
        comps: Set[str]
        if load_keys is not None and not isinstance(load_keys, set):
            raise PersistableError(
                f'Expecting set but got {load_keys} {type(load_keys)}')
        for group in groups:
            if not isinstance(group, set):
                raise PersistableError(
                    f'Composition not set: {group} ({type(group)})')
            name = '-'.join(sorted(group))
            path = comp_path / name
            comp_stash = DirectoryStash(path)
            comp_stash.group = group
            comp_stash.group_name = name
            for k in group:
                if k in stashes:
                    raise PersistableError(
                        f'Duplicate name \'{k}\' in {groups}')
                stashes[k] = comp_stash
                self.stash_by_group[name] = comp_stash
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'creating composit hash with groups: {self.groups}')

    def clear(self):
        logger.info('DirectoryCompositeStash: clearing')
        if self.top_level_dir.is_dir():
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'deleting subtree: {self.top_level_dir}')
            shutil.rmtree(self.top_level_dir)

    def _to_composite(self, data: dict) -> Tuple[str, Any, Tuple[str, Any]]:
        """Create the composite data used to by the composite stashes to persist.

        :param data: the data item stored as the attribute in ``inst`` to
                     persist

        :return: a tuple with the following:
                 * attribute name
                 * original attriubte value to be repopulated after pickling
                 * context used when loading, which is the ordered keys for now
                 * list of tuples each having (stash name, data dict)

        """
        data_group = collections.defaultdict(lambda: {})
        is_ordered = isinstance(data, collections.OrderedDict)
        context = tuple(data.keys()) if is_ordered else None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'keys: {data.keys()}, groups: {self.all_keys}')
        missing_keys: Set[str] = self.all_keys - set(data.keys())
        if len(missing_keys) > 0:
            raise MissingDataKeys(missing_keys)
        for k, v in data.items():
            if k not in self.stash_by_attribute:
                raise PersistableError(
                    f'Unmapping/grouped attribute: {k} in {self.groups}')
            stash = self.stash_by_attribute[k]
            data_group[stash.group_name][k] = v
        data_group = tuple(data_group.items())
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'create group {data_group}')
        return context, data_group

    def dump(self, name: str, inst: Any):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'dump {name}({self.attribute_name}) ' +
                         f'-> {inst.__class__}')
        org_attr_val = getattr(inst, self.attribute_name)
        context, composite = self._to_composite(org_attr_val)
        try:
            setattr(inst, self.attribute_name, None)
            for group_name, composite_inst in composite:
                stash = self.stash_by_group[group_name]
                stash.dump(name, composite_inst)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'dump composite {group_name}/{name}: ' +
                                 f'context={context}, inst={composite_inst}')
            super().dump(name, (inst, context))
        finally:
            setattr(inst, self.attribute_name, org_attr_val)

    def _from_composite(self, name: str, context: Any) -> Any:
        """Restore the item's attribute ``dict`` values on load.

        :param name: the ID key of the data item used in the composite stashes

        :param context: the load context (see :meth:`_to_composite`)

        """
        attr_name = self.attribute_name
        comp_data = {}
        attribs = set(self.stash_by_attribute.keys())
        if self.load_keys is not None:
            attribs = attribs & self.load_keys
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'load attribs: {attribs}')
        for stash in self.stash_by_group.values():
            if len(stash.group & attribs) > 0:
                data = stash.load(name)
                logger.debug(f'loaded: {data}')
                if data is None:
                    raise PersistableError(
                        f'Missing composite data for id: {name}, ' +
                        f'stash: {stash.group}, path: {stash.path}, ' +
                        f'attribute: \'{attr_name}\'')
                if self.load_keys is None:
                    comp_data.update(data)
                else:
                    for k in set(data.keys()) & attribs:
                        comp_data[k] = data[k]
        if context is not None:
            ordered_data = collections.OrderedDict()
            for k in context:
                if k in comp_data:
                    ordered_data[k] = comp_data[k]
            comp_data = ordered_data
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'comp_data: {comp_data}')
        return comp_data

    def load(self, name: str) -> Any:
        inst, context = super().load(name)
        attr_val = self._from_composite(name, context)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'loaded {name}({self.attribute_name})')
        setattr(inst, self.attribute_name, attr_val)
        return inst
