"""Utility classes to help with dataclasses.

"""
__author__ = 'Paul Landes'

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import re
import ast
import inspect
from . import ClassImporter

logger = logging.getLogger(__name__)


class ClassError(Exception):
    """Raised by :class:`.ClassInspector.` when a class can not be inspected or
    parsed by :mod:`ast`.

    """
    pass


@dataclass
class TypeMapper(object):
    """A utility class to map string types parsed from :class:`.ClassInspector`
    to Python types.

    """
    DEFAULT_DATA_TYPES = {t.__name__: t
                          for t in [str, int, float, bool, list, Path]}
    """Supported data types mapped from data class fields."""

    cls: type = field()
    """The class to map."""

    data_types: Dict[str, type] = field(default=None)
    """Data type mapping for this instance."""

    default_type: type = field(default=str)
    """Default type for when no type is given."""

    allow_enum: bool = field(default=True)
    """Whether or not to allow :class:`.Enum` as an acceptable type.  When the
    mapper encouters these classes, the class is loaded from the module and
    returned as a type.

    """

    def __post_init__(self):
        if self.data_types is None:
            self.data_types = self.DEFAULT_DATA_TYPES

    def _try_enum(self, stype: str) -> type:
        """Try to resolve ``stype`` as an :class:`.Enum' class.

        """
        mod = self.cls.__module__
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'module: {mod}')
        class_name = f'{mod}.{stype}'
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'trying to load {class_name}')
        ci = ClassImporter(class_name, reload=False)
        cls: type = ci.get_class()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'successfully loaded class {cls}')
        if issubclass(cls, Enum):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'mapping {cls} from {stype}')
        return cls

    def map_type(self, stype: str = None) -> type:
        if stype is None:
            tpe = self.default_type
        else:
            tpe = self.data_types.get(stype)
        if tpe is None and self.allow_enum:
            try:
                tpe = self._try_enum(stype)
            except Exception as e:
                logger.error('could not narrow to enum: {stype}', e)
        if tpe is None:
            raise ClassError(f'non-supported data type: {stype}')
        return tpe


@dataclass(eq=True)
class ClassDoc(object):
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
class ClassParam(object):
    """Represents a :class:`dataclasses.dataclass` field.

    """
    name: str = field()
    """The name of the field."""

    dtype: type = field()
    """The data type."""

    doc: ClassDoc = field()
    """The documentation of the field."""


@dataclass(eq=True)
class ClassField(ClassParam):
    """Represents a :class:`dataclasses.dataclass` field.

    """
    kwargs: Dict[str, Any] = field()
    """The field arguments."""

    @property
    def default(self) -> Any:
        if self.kwargs is not None:
            return self.kwargs.get('default')


@dataclass(eq=True)
class ClassMethodArg(ClassParam):
    """Meta data for an argument in a method.

    """
    default: str = field()
    """The default if any, otherwise ``None``."""

    is_positional: bool = field()
    """``True`` is the argument is positional vs. a keyword argument."""


@dataclass(eq=True)
class ClassMethod(object):
    """Meta data for a method in a dataclass.

    """
    name: str = field()
    """The name of the method."""

    doc: ClassDoc = field()
    """The docstring of the method."""

    args: Tuple[ClassMethodArg] = field()
    """The arguments of the method."""


@dataclass(eq=True)
class Class(object):
    class_type: type = field()
    """The class that was inspected."""

    doc: ClassDoc = field()
    """The docstring of the class."""

    fields: Dict[str, ClassField] = field()
    """The fields of the class."""

    methods: Dict[str, ClassMethod] = field()
    """The methods of the class."""

    @property
    def name(self) -> str:
        return ClassImporter.full_classname(self.class_type)


@dataclass
class ClassInspector(object):
    """A utility class to return all :class:`dataclasses.dataclass` attribute
    (field) documentation.

    """
    cls: type = field()
    """The class to inspect."""

    attrs: Tuple[str] = field(default=None)
    """The class attributes to inspect, or all found are returned when ``None``.

    """

    data_type_mapper: TypeMapper = field(default=None)
    """The mapper used for narrowing a type from a string parsed from the Python
    AST.

    """

    def __post_init__(self):
        self.data_type_mapper = TypeMapper(self.cls)

    def _get_class_node(self) -> ast.AST:
        fname = inspect.getfile(self.cls)
        logger.debug(f'parsing source file: {fname}')
        with open(fname, 'r') as f:
            fstr = f.read()
        for node in ast.walk(ast.parse(fstr)):
            if isinstance(node, ast.ClassDef):
                if node.name == self.cls.__name__:
                    return node

    def _map_default(self, def_node: ast.AST):
        """Map a default from what will be at times an :class:`ast.Name`.  This happens
        when an enum is used as a type, but name.id only give the enum class
        name and not the enum value

        """
        if isinstance(def_node, ast.Attribute):
            enum_name: str = def_node.attr
            cls: type = self.data_type_mapper.map_type(def_node.value.id)
            default = cls.__members__[enum_name]
        # ast.Num and ast.Str added for Python 3.7 backward compat
        elif isinstance(def_node, ast.Num):
            default = def_node.n
        elif isinstance(def_node, ast.Str):
            default = def_node.s
        else:
            default = def_node.value
        return default

    def _get_args(self, node: ast.arguments):
        args = []
        defaults = node.defaults
        dsidx = len(node.args) - len(defaults)
        for i, arg in enumerate(node.args):
            name = arg.arg
            try:
                dtype = None
                is_positional = True
                default = None
                didx = i - dsidx
                if didx >= 0:
                    default = self._map_default(defaults[didx])
                    is_positional = False
                if arg.annotation is not None:
                    dtype = arg.annotation.id
                dtype = self.data_type_mapper.map_type(dtype)
                arg = ClassMethodArg(name, dtype, None, default, is_positional)
            except Exception as e:
                raise ClassError(f'could not map argument {name}: {e}')
            args.append(arg)
        return args

    def _get_method(self, node: ast.FunctionDef) -> ClassMethod:
        method: ClassMethod = None
        name = node.name
        is_priv = name.startswith('_')
        is_prop = any(map(lambda n: n.id, node.decorator_list))
        # only public methods (not properties) are parsed for now
        if not is_prop and not is_priv:
            args = self._get_args(node.args)
            node = None if len(node.body) == 0 else node.body[0]
            # parse the docstring for instance methods only
            if (node is not None) and (len(args) > 0) and \
               (args[0].name == 'self'):
                args = args[1:]
            else:
                args = ()
            if isinstance(node, ast.Expr) and \
               isinstance(node.value, ast.Constant):
                doc = ClassDoc(node.value.value)
            # ast.Str added for Python 3.7 backward compat
            elif isinstance(node, ast.Expr) and \
                 isinstance(node.value, ast.Str):
                doc = ClassDoc(node.value.s)
            else:
                doc = None
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'doc: {name}: {doc}')
            method = ClassMethod(name, doc, args)
            # copy the parsed parameter doc found in the method doc to the
            # argument meta data
            if (method.doc is not None) and \
               (method.doc.params is not None) and \
               (method.args is not None):
                for arg in method.args:
                    param = method.doc.params.get(arg.name)
                    if (param is not None) and (arg.doc is None):
                        arg.doc = ClassDoc(param, None)
        return method

    def get_class(self) -> Class:
        """Return a dict of attribute (field) to metadata and docstring.

        """
        attrs = self.attrs
        if attrs is None:
            attrs = tuple(filter(lambda i: i[:1] != '_',
                                 self.cls.__dict__.keys()))
        cnode: ast.Node = self._get_class_node()
        fields: List[ClassField] = []
        methods: List[ClassMethod] = []
        for node in cnode.body:
            # parse the dataclass attribute/field defintion
            if isinstance(node, ast.AnnAssign) and \
               isinstance(node.annotation, ast.Name):
                name: str = node.target.id
                dtype: str = node.annotation.id
                dtype: type = self.data_type_mapper.map_type(dtype)
                if node.value is not None:
                    kwlst: List[ast.keyword] = node.value.keywords
                    kwargs = {k.arg: self._map_default(k.value) for k in kwlst}
                    fields.append(ClassField(name, dtype, None, kwargs))
            # parse documentation string right after the dataclass field
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Constant) and
                  len(fields) > 0):
                doc = ClassDoc(node.value.value)
                last_field: ClassField = fields[-1]
                if last_field.doc is None:
                    last_field.doc = doc
            # ast.Str added for Python 3.7 backward compat
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Str) and
                  len(fields) > 0):
                doc = ClassDoc(node.value.s)
                last_field: ClassField = fields[-1]
                if last_field.doc is None:
                    last_field.doc = doc
            # parse the method
            elif isinstance(node, ast.FunctionDef):
                meth = self._get_method(node)
                if meth is not None:
                    methods.append(meth)
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'not processed node: {type(node)}: ' +
                                 f'{node.value}')
        return Class(
            self.cls,
            ClassDoc(self.cls.__doc__),
            fields={d.name: d for d in fields},
            methods={m.name: m for m in methods})
