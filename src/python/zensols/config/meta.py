"""This file contains utility classes for exploring complex instance graphs.
This is handy for deeply nested ``Stash`` instances.

"""
__author__ = 'Paul Landes'

import dataclasses
from typing import Set, Type, Any
import logging
import sys
import collections
from io import TextIOBase
from zensols.config import ClassResolver, Writable

logger = logging.getLogger(__name__)


class ClassExplorer(Writable):
    """A utility class that recursively reports class metadata in an object graph.

    """
    ATTR_META_NAME = 'ATTR_EXP_META'
    """The attribute name set on classes to find to report their fields.  When the
    value of this is set as a class attribute, each of that object instances'
    members are pretty printed.  The value is a tuple of string attribute
    names.

    """

    def __init__(self, include_classes: Set[Type],
                 exclude_classes: Set[Type] = None,
                 indent: int = 4, attr_truncate_len: int = 80,
                 include_dicts: bool = False,
                 include_private: bool = False,
                 dictify_dataclasses: bool = False):
        self.include_classes = include_classes
        if exclude_classes is None:
            self.exclude_classes = set()
        else:
            self.exclude_classes = exclude_classes
        self.indent = indent
        self.attr_truncate_len = attr_truncate_len
        self.include_dicts = include_dicts
        self.include_private = include_private
        self.dictify_dataclasses = dictify_dataclasses

    def get_metadata(self, inst: Any) -> dict:
        self.visited = set()
        try:
            include_classes = set(self.include_classes | set([inst.__class__]))
            meta = self._get_metadata(
                inst, tuple(include_classes), tuple(self.exclude_classes))
        finally:
            del self.visited
        return meta

    def _get_dict(self, inst: dict, include_classes: Set[Type],
                  exclude_classes: Set[Type]) -> dict:
        oid = id(inst)
        if oid not in self.visited:
            children = []
            self.visited.add(oid)
            for k, v in inst.items():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'desc {k} -> {type(v)}')
                v = self._get_metadata(v, include_classes, exclude_classes)
                if v is not None:
                    children.append({'attr': k, 'child': v})
            return {'class_name': '<dict>', 'children': children}

    def _is_traversable(self, inst: Any, include_classes: Set[Type],
                        exclude_classes: Set[Type]) -> bool:
        return isinstance(inst, include_classes) and \
            not isinstance(inst, exclude_classes)

    def _get_metadata(self, inst: Any, include_classes: Set[Type],
                      exclude_classes: Set[Type]) -> dict:
        oid = id(inst)
        if oid in self.visited:
            return None
        self.visited.add(oid)
        dat = None
        if self.include_dicts and isinstance(inst, dict):
            dat = self._get_dict(inst, include_classes, exclude_classes)
        elif self._is_traversable(inst, include_classes, exclude_classes):
            dat = collections.OrderedDict()
            cls = inst.__class__
            class_name = ClassResolver.full_classname(cls)
            children = []
            dat['class_name'] = class_name
            is_dataclass = self.dictify_dataclasses and \
                dataclasses.is_dataclass(inst)
            has_attr_meta = hasattr(cls, self.ATTR_META_NAME)
            if hasattr(inst, 'name'):
                dat['name'] = getattr(inst, 'name')
            if has_attr_meta or is_dataclass:
                attrs = {}
                dat['attrs'] = attrs
                if not has_attr_meta and is_dataclass:
                    try:
                        attr_names = dataclasses.asdict(inst)
                    except Exception as e:
                        logger.info(
                            f'can not get attr names for {type(inst)}: {e}')
                        attr_names = ()
                elif has_attr_meta:
                    attr_names = getattr(cls, self.ATTR_META_NAME)
                # TODO: skip attributes that will or have already been
                # traversed as a "traversable" object on a recursion
                for attr in attr_names:
                    v = getattr(inst, attr)
                    if isinstance(v, dict):
                        v = self._get_dict(v, include_classes, exclude_classes)
                        if v is not None:
                            children.append({'attr': attr, 'child': v})
                    else:
                        attrs[attr] = v
            for attr in inst.__dir__():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'desc meta: {type(inst)}.{attr}')
                if self.include_private or not attr.startswith('_'):
                    try:
                        child_inst = getattr(inst, attr)
                    except Exception as e:
                        msg = f'error: can not traverse attribute {attr}: {e}'
                        logger.info(msg)
                        child_inst = msg
                    if isinstance(child_inst, dict):
                        child = self._get_dict(
                            child_inst, include_classes, exclude_classes)
                    else:
                        child = self._get_metadata(
                            child_inst, include_classes, exclude_classes)
                    if child is not None:
                        children.append({'attr': attr, 'child': child})
            if len(children) > 0:
                dat['children'] = children
        return dat

    def write(self, inst: Any, depth: int = 0,
              writer: TextIOBase = sys.stdout):
        meta = self.get_metadata(inst)
        self._write(meta, depth, None, writer)

    def write_metadata(self, depth: int = 0,
                       writer: TextIOBase = sys.stdout,
                       metadata: dict = None):
        self._write(metadata, depth, None, writer)
        
    def _write(self, metadata: dict, depth: int, attr: str, writer):
        cn = f'{attr}: ' if attr is not None else ''
        name = f" ({metadata['name']})" if 'name' in metadata else ''
        sp = self._sp(depth)
        sp2 = self._sp(depth + 1)
        writer.write(f"{sp}{cn}{metadata['class_name']}{name}\n")
        if 'attrs' in metadata:
            for k, v in metadata['attrs'].items():
                v = self._trunc(str(v), max_len=self.attr_truncate_len)
                writer.write(f'{sp2}{k}: {v}\n')
        if 'children' in metadata:
            for c in metadata['children']:
                self._write(c['child'], depth + 1, c['attr'], writer)
