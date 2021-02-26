"""Utility classes to help with dataclasses.

"""
__author__ = 'Paul Landes'

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, field
import logging
from itertools import chain
import re
import ast
import inspect

logger = logging.getLogger(__name__)


@dataclass(eq=True)
class DataClassDoc(object):
    """A meta data for documentation at any level of the class code (methods etc).

    """
    PARAM_REGEX = re.compile(r'^\s*:param ([^:]+):\s*(.+)$')
    """Matches :param: documentation."""

    text: str = field()
    """The text of the documentation."""

    params: Dict[str, str] = field(default=None)
    """The parsed parameter documentation."""

    def __post_init__(self):
        doc, params = self._parse_params(self.text)
        if doc is not None:
            doc = doc.strip()
            if len(doc) == 0:
                doc = None
            else:
                doc = doc.lower()
                if doc[-1] == '.':
                    doc = doc[0:-1]
        self.text = doc
        self.params = params

    def _parse_params(self, text: str) -> Dict[str, str]:
        doc_lines = []
        params: Dict[str, List[str]] = {}
        last_param = None
        param_sec = False
        for line in text.split('\n'):
            line = line.strip()
            if len(line) > 0:
                m = self.PARAM_REGEX.match(line)
                if m is None:
                    if param_sec:
                        last_param.append(line)
                    else:
                        doc_lines.append(line)
                else:
                    name, doc = m.groups()
                    last_param = [doc]
                    params[name] = last_param
                    param_sec = True
        param_doc = {}
        for k, v in params.items():
            param_doc[k] = ' '.join(v)
        doc = ' '.join(doc_lines)
        return doc, param_doc


@dataclass(eq=True)
class DataClassParam(object):
    """Represents a :class:`dataclasses.dataclass` field.

    """
    name: str = field()
    """The name of the field."""

    dtype: type = field()
    """The data type."""

    doc: DataClassDoc = field()
    """The documentation of the field."""


@dataclass(eq=True)
class DataClassField(DataClassParam):
    """Represents a :class:`dataclasses.dataclass` field.

    """
    kwargs: Dict[str, Any] = field()
    """The field arguments."""

    @property
    def default(self) -> Any:
        if self.kwargs is not None:
            return self.kwargs.get('default')


@dataclass(eq=True)
class DataClassMethodArg(DataClassParam):
    """Meta data for an argument in a method.

    """
    default: str = field()
    """The default if any, otherwise ``None``."""

    is_positional: bool = field()
    """``True`` is the argument is positional vs. a keyword argument."""


@dataclass(eq=True)
class DataClassMethod(object):
    """Meta data for a method in a dataclass.

    """
    name: str = field()
    """The name of the method."""

    doc: DataClassDoc = field()
    """The docstring of the method."""

    args: Tuple[DataClassMethodArg] = field()
    """The arguments of the method."""


@dataclass(eq=True)
class DataClass(object):
    cls: type = field()
    """The class that was inspected."""

    doc: DataClassDoc = field()
    """The docstring of the class."""

    fields: Dict[str, DataClassField] = field()
    """The fields of the class."""

    methods: Dict[str, DataClassMethod] = field()
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
            is_positional = True
            default = None
            didx = i - dlen - 1
            if didx < len(defaults) and didx >= 0:
                default = defaults[didx].value
                is_positional = False
            if arg.annotation is not None:
                dtype = arg.annotation.id
            arg = DataClassMethodArg(name, dtype, None, default, is_positional)
            args.append(arg)
        return args

    def _get_method(self, node: ast.FunctionDef) -> DataClassMethod:
        method: DataClassMethod = None
        name = node.name
        is_priv = name.startswith('_')
        is_prop = any(map(lambda n: n.id, node.decorator_list))
        if not is_prop and not is_priv:
            args = self._get_args(node.args)
            node = None if len(node.body) == 0 else node.body[0]
            # parse the docstring for instance methods only
            if (node is not None) and (len(args) > 0) and \
               (args[0].name == 'self'):
                args = args[1:]
            else:
                args = ()
            if (isinstance(node, ast.Expr) and
                isinstance(node.value, ast.Constant)):
                doc = DataClassDoc(node.value.value)
            else:
                doc = None
            method = DataClassMethod(name, doc, args)
        return method

    def get_meta_data(self) -> DataClass:
        """Return a dict of attribute (field) to metadata and docstring.

        """
        attrs = self.attrs
        if attrs is None:
            attrs = tuple(filter(lambda i: i[:1] != '_',
                                 self.cls.__dict__.keys()))
        cnode: ast.Node = self._get_class_node()
        fields: List[DataClassField] = []
        methods: List[DataClassMethod] = []
        for node in cnode.body:
            # parse the dataclass attribute/field defintion
            if isinstance(node, ast.AnnAssign):
                name: str = node.target.id
                dtype: str = node.annotation.id
                kwlst: List[ast.keyword] = node.value.keywords
                kwargs = {k.arg: k.value.value for k in kwlst}
                fields.append(DataClassField(name, dtype, None, kwargs))
            # parse documentation string right after the dataclass field
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Constant) and
                  len(fields) > 0):
                doc = DataClassDoc(node.value.value)
                last_field: DataClassField = fields[-1]
                if last_field.doc is None:
                    last_field.doc = doc
            # parse the method
            elif isinstance(node, ast.FunctionDef):
                meth = self._get_method(node)
                if meth is not None:
                    methods.append(meth)
        return DataClass(
            self.cls,
            DataClassDoc(self.cls.__doc__),
            fields={d.name: d for d in fields},
            methods={m.name: m for m in methods})
