"""Very simple object relational mapping.

"""
__author__ = 'Paul Landes'
from typing import Type, Any
from dataclasses import dataclass, field, Field
import dataclasses
import logging
import re
import ast
import inspect
import textwrap
from ..config import Dictable
from ..persist import persisted
from ..introspect.imp import ClassImporter
from ..introspect.insp import ClassDoc
from ..introspect.insp import ClassField as IntrospectClassField

logger = logging.getLogger(__name__)


@dataclass
class ClassField(IntrospectClassField, Dictable):
    """Stash column metadata that repreesnts a :class:`dataclasses.dataclass`.

    """
    data_field: Field = field(repr=False)
    """The field data from the dataclass."""

    @staticmethod
    def _flatten_class_field(data: dict[str, Any]):
        data['dtype'] = str(data['dtype'].__name__)
        return data

    def _flatten_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        data = self._flatten_class_field(data)
        data = super()._flatten_dict(data)
        return data

    def __str__(self) -> str:
        return f'{self.name} ({self.dtype.__name__})'

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class DataclassMetadata(Dictable):
    """This class provides introspection access and metadata to
    :class:`~dataclass.dataclass` instances.

    """
    _DICTABLE_ATTRIBUTES = {'fields_by_order', 'doc'}

    class_type: Type = field()
    """The dataclass to map."""

    def _flatten_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        data['class_type'] = str(data['class_type'])
        data['fields_by_order'] = tuple(map(
            ClassField._flatten_class_field, data['fields_by_order']))
        data['class_type'] = ClassImporter.full_classname(self.class_type)
        dct = super()._flatten_dict(data)
        return dct

    def _get_attribute_docstrings(self) -> dict[str, str]:
        cls: Type = self.class_type
        source = inspect.getsource(cls)
        source = textwrap.dedent(source)
        tree = ast.parse(source)
        class_node = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == cls.__name__)
        docs: dict[str, str] = {}
        prev_field_name: str = None
        for node in class_node.body:
            if isinstance(node, ast.AnnAssign):
                # name: str = field()
                # icon: str
                if isinstance(node.target, ast.Name):
                    prev_field_name = node.target.id
                else:
                    prev_field_name = None
            elif isinstance(node, ast.Assign):
                # name = field()
                if len(node.targets) == 1 and \
                   isinstance(node.targets[0], ast.Name):
                    prev_field_name = node.targets[0].id
                else:
                    prev_field_name = None
            elif (prev_field_name is not None and
                  isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Constant) and
                  isinstance(node.value.value, str)):
                doc: str = inspect.cleandoc(node.value.value)
                doc = re.sub(r'\s+', ' ', doc).strip()
                docs[prev_field_name] = doc
                prev_field_name = None
            else:
                prev_field_name = None
        return docs

    @property
    @persisted('_fields_by_order')
    def fields_by_order(self) -> tuple[ClassField, ...]:
        """Create field metadata for :obj:`class_type`."""
        def map_field(f: Field) -> ClassField:
            doc: str = docs.get(f.name)
            return ClassField(
                name=f.name,
                dtype=f.type,
                doc=None if doc is None else ClassDoc(doc),
                kwargs={},
                data_field=f)

        docs: dict[str, str] = self._get_attribute_docstrings()
        return tuple(map(map_field, dataclasses.fields(self.class_type)))

    @property
    def fields(self) -> dict[str, ClassField]:
        """The fields of the class."""
        return dict(map(lambda m: (m.name, m), self.fields_by_order))

    @property
    @persisted('_doc')
    def doc(self) -> ClassDoc:
        """The docstring of the class."""
        return ClassDoc(self.class_type.__doc__)

    def _write(self, c):
        c(str(self.class_type), 'class_type')
        c(self.doc.text, 'doc')
        meta: ClassField
        for meta in self.fields_by_order:
            fd: dict[str, Any] = meta.asdict()
            c(f"{fd.pop('name')}:")
            c(fd, depth=1)
