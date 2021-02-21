"""Utility classes to help with dataclasses.

"""
__author__ = 'Paul Landes'

from typing import List, Tuple, Dict
from dataclasses import dataclass, field
import logging
import ast
import inspect

logger = logging.getLogger(__name__)


@dataclass
class FieldDoc(object):
    name: str
    dtype: type
    text: str = field(default=None)


@dataclass
class DataClassInspector(object):
    cls: type
    attrs: Tuple[str] = field(default=None)

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

    def get_field_docs(self) -> Dict[str, str]:
        """Read the class source file and return a dict with global variables, their
        value and the *docstring* that follows the definition of the variable.

        """
        attrs = self.attrs
        if attrs is None:
            attrs = tuple(filter(lambda i: i[:1] != '_',
                                 self.cls.__dict__.keys()))
        nodes: List[ast.Node] = self._get_class_nodes()
        docs: List[FieldDoc] = []
        for node in nodes:
            if isinstance(node, ast.AnnAssign):
                name: str = node.target.id
                dtype: str = node.annotation.id
                docs.append(FieldDoc(name, dtype))
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Constant) and
                  len(docs) > 0):
                text = node.value.value
                last_doc: FieldDoc = docs[-1]
                if last_doc.text is None:
                    last_doc.text = text
        return {d.name: d for d in docs}
