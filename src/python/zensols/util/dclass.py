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
class DataClassFieldMetaData(object):
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
class DataClassMethodMetaDataArg(object):
    """Meta data for an argument in a method.

    """
    name: str = field()
    """The name of the argument."""

    default: str = field()
    """The default if any, otherwise ``None``."""

    dtype: str = field()
    """The data type as a typehint, or ``None`` if not given."""


@dataclass
class DataClassMethodMetaData(object):
    """Meta data for a method in a dataclass.

    """
    name: str = field()
    """The name of the method."""

    doc: str = field()
    """The docstring of the method."""

    args: Tuple[DataClassMethodMetaDataArg] = field()
    """The arguments of the method."""


@dataclass
class DataClassMetaData(object):
    cls: type = field()
    """The class that was inspected."""

    doc: str = field()
    """The docstring of the class."""

    fields: Dict[str, DataClassFieldMetaData] = field()
    """The fields of the class."""

    methods: Dict[str, DataClassMethodMetaData] = field()
    """The methods of the class."""


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

    def _get_args(self, node: ast.arguments):
        args = []
        defaults = node.defaults
        dlen = len(defaults)
        for i, arg in enumerate(node.args):
            name = arg.arg
            dtype = None
            default = None
            didx = i - dlen - 1
            if didx >= 0:
                default = defaults[didx].value
            if arg.annotation is not None:
                dtype = arg.annotation.id
            arg = DataClassMethodMetaDataArg(name, default, dtype)
            args.append(arg)
        return args

    def _get_method(self, node: ast.FunctionDef) -> DataClassMethodMetaData:
        method: DataClassMethodMetaData = None
        is_prop = any(map(lambda n: n.id, node.decorator_list))
        if node.args is not None and not is_prop:
            name = node.name
            args = self._get_args(node.args)
            node = None if len(node.body) == 0 else node.body[0]
            if node is not None and len(args) > 0 and args[0].name == 'self':
                if isinstance(node, ast.Expr) and \
                   isinstance(node.value, ast.Constant):
                    method = DataClassMethodMetaData(name, node.value.value, args[1:])
        return method

    def get_meta_data(self) -> DataClassMetaData:
        """Return a dict of attribute (field) to metadata and docstring.

        """
        attrs = self.attrs
        if attrs is None:
            attrs = tuple(filter(lambda i: i[:1] != '_',
                                 self.cls.__dict__.keys()))
        cnode: ast.Node = self._get_class_node()
        fields: List[DataClassFieldMetaData] = []
        methods: List[DataClassMethodMetaData] = []
        for node in cnode.body:
            # parse the dataclass attribute/field defintion
            if isinstance(node, ast.AnnAssign):
                name: str = node.target.id
                dtype: str = node.annotation.id
                kwlst: List[ast.keyword] = node.value.keywords
                kwargs = {k.arg: k.value.value for k in kwlst}
                fields.append(DataClassFieldMetaData(name, dtype, kwargs))
            # parse documentation string right after the dataclass field
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Constant) and
                  len(fields) > 0):
                doc = node.value.value
                last_doc: DataClassFieldMetaData = fields[-1]
                if last_doc.doc is None:
                    last_doc.doc = doc
            # parse the method
            elif isinstance(node, ast.FunctionDef):
                meth = self._get_method(node)
                if meth is not None:
                    methods.append(meth)
        return DataClassMetaData(
            self.cls,
            self.cls.__doc__,
            fields={d.name: d for d in fields},
            methods={m.name: m for m in methods})
