"""This file contains utility classes for exploring complex instance graphs.
This is handy for deeply nested ``Stash`` instances.

"""
__author__ = 'Paul Landes'


from typing import Set, Type
import sys
import collections
from io import TextIOWrapper
from zensols.config import ClassResolver, Writable


class ClassExplorer(Writable):
    ATTR_META_NAME = 'ATTR_EXP_META'

    def __init__(self, include_classes: Set[Type],
                 exclude_classes: Set[Type] = frozenset(),
                 indent=4, attr_truncate_len=80):
        self.include_classes = include_classes
        self.exclude_classes = include_classes
        self.indent = indent
        self.attr_truncate_len = attr_truncate_len

    def get_metadata(self, inst: object) -> dict:
        include_classes = set(self.include_classes | set([inst.__class__]))
        return self._get_metadata(inst, include_classes, self.exclude_classes)

    def _should_explore(self, inst: object, include_classes: Set[Type],
                        exclude_classes: Set[Type]) -> bool:
        has_inc = any(map(lambda t: isinstance(inst, t), include_classes))
        has_exc = any(map(lambda t: isinstance(inst, t), exclude_classes))
        return has_inc and not has_exc

    def _get_metadata(self, inst: object, include_classes: Set[Type],
                      exclude_classes: Set[Type]) -> dict:
        dat = None
        self._should_explore(inst, include_classes, exclude_classes)
        if any(map(lambda t: isinstance(inst, t), include_classes)):
            dat = collections.OrderedDict()
            cls = inst.__class__
            class_name = ClassResolver.full_classname(cls)
            children = []
            dat['class_name'] = class_name
            if hasattr(inst, 'name'):
                dat['name'] = getattr(inst, 'name')
            if hasattr(cls, self.ATTR_META_NAME):
                attrs = {}
                dat['attrs'] = attrs
                for attr in getattr(cls, self.ATTR_META_NAME):
                    attrs[attr] = getattr(inst, attr)
            for attr in inst.__dir__():
                child_inst = getattr(inst, attr)
                child = self._get_metadata(
                    child_inst, include_classes, exclude_classes)
                if child is not None:
                    children.append({'attr': attr, 'child': child})
            if len(children) > 0:
                dat['children'] = children
        return dat

    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout,
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
                v = str(v)
                v = v[:self.attr_truncate_len]
                writer.write(f'{sp2}{k}: {v}\n')
        if 'children' in metadata:
            for c in metadata['children']:
                self._write(c['child'], depth + 1, c['attr'], writer)
