"""Utility classes to help with dataclasses.

"""
__author__ = 'Paul Landes'

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, field
import logging
import ast
import inspect

logger = logging.getLogger(__name__)


@dataclass(eq=True)
class FieldMetaData(object):
    """Represents a :class:`dataclasses.dataclass` field.

    """
    name: str = field()
    """The name of the field."""

    dtype: type = field()
    """The data type."""

    kwargs: Dict[str, Any] = field()
    """The field arguments."""

    doc: str = field(default=None)
    """The documentation of the field."""

    @property
    def default(self) -> Any:
        if self.kwargs is not None:
            return self.kwargs.get('default')


@dataclass
class DataClassMetaData(object):
    cls: type = field()
    """The class that was inspected."""

    fields: Dict[str, FieldMetaData] = field()
    """The fields of the class."""


@dataclass
class DataClassInspector(object):
    """A utility class to return all :class:`dataclasses.dataclass` attribute
    (field) documentation.

    """
    cls: type = field()
    """The class to inspect."""

    attrs: Tuple[str] = field(default=None)
    """The attributes to find documentation, or all found are returned when
    ``None``.

    """

    def _get_class_node(self) -> ast.AST:
        fname = inspect.getfile(self.cls)
        logger.debug(f'parsing source file: {fname}')
        with open(fname, 'r') as f:
            fstr = f.read()
        for node in ast.walk(ast.parse(fstr)):
            if isinstance(node, ast.ClassDef):
                if node.name == self.cls.__name__:
                    return node

    def get_meta_data(self) -> DataClassMetaData:
        """Return a dict of attribute (field) to metadata and docstring.

        """
        attrs = self.attrs
        if attrs is None:
            attrs = tuple(filter(lambda i: i[:1] != '_',
                                 self.cls.__dict__.keys()))
        cnode: ast.Node = self._get_class_node()
        docs: List[FieldMetaData] = []
        for node in cnode.body:
            if isinstance(node, ast.AnnAssign):
                name: str = node.target.id
                dtype: str = node.annotation.id
                kwlst: List[ast.keyword] = node.value.keywords
                kwargs = {k.arg: k.value.value for k in kwlst}
                docs.append(FieldMetaData(name, dtype, kwargs))
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Constant) and
                  len(docs) > 0):
                doc = node.value.value
                last_doc: FieldMetaData = docs[-1]
                if last_doc.doc is None:
                    last_doc.doc = doc
        return DataClassMetaData(self.cls, {d.name: d for d in docs})
