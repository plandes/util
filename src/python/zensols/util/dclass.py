"""Utility classes to help with dataclasses.

"""
__author__ = 'Paul Landes'

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, field
import logging
import ast
import inspect

logger = logging.getLogger(__name__)


@dataclass
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

    def _get_class_nodes(self) -> List[ast.AST]:
        cls = self.cls
        fname = inspect.getfile(cls)
        logger.debug(f'parsing source file: {fname}')
        with open(fname, 'r') as f:
            fstr = f.read()
        class_nodes = []
        for node in ast.walk(ast.parse(fstr)):
            if isinstance(node, ast.ClassDef):
                if node.name == cls.__name__:
                    class_nodes.extend(node.body)
        return class_nodes

    def get_field_docs(self) -> Dict[str, FieldMetaData]:
        """Return a dict of attribute (field) to metadata and docstring.

        """
        attrs = self.attrs
        if attrs is None:
            attrs = tuple(filter(lambda i: i[:1] != '_',
                                 self.cls.__dict__.keys()))
        nodes: List[ast.Node] = self._get_class_nodes()
        docs: List[FieldMetaData] = []
        for node in nodes:
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
        return {d.name: d for d in docs}
