"""Utility classes to help with dataclasses.

"""
__author__ = 'Paul Landes'

from typing import List, Tuple, Dict, Any, Type, Optional, ClassVar
from dataclasses import dataclass, field
import dataclasses
import logging
from collections import OrderedDict
import re
import ast
import inspect
from inspect import Parameter, Signature
from pathlib import Path
from . import ClassImporter, IntegerSelection

logger = logging.getLogger(__name__)


class ClassError(Exception):
    """Raised by :class:`.ClassInspector.` when a class can not be inspected or
    parsed by :mod:`ast`.

    """
    pass


def _create_data_types() -> Dict[str, Type]:
    types = {t.__name__: t for t in
             [str, int, float, bool, list, dict, Path, IntegerSelection]}
    types['pathlib.Path'] = Path
    return types


DEFAULT_DATA_TYPES: Dict[str, Type] = _create_data_types()


@dataclass
class TypeMapper(object):
    """A utility class to map string types parsed from :class:`.ClassInspector`
    to Python types.

    """
    DEFAULT_DATA_TYPES: ClassVar[Dict[str, Type]] = _create_data_types()
    """Supported data types mapped from data class fields."""

    cls: Type = field()
    """The class to map."""

    data_types: Dict[str, Type] = field(
        default_factory=lambda: DEFAULT_DATA_TYPES)
    """Data type mapping for this instance."""

    default_type: Type = field(default=str)
    """Default type for when no type is given."""

    allow_class: bool = field(default=True)
    """Whether or not to allow classes acceptable types.  When the mapper
    encouters these classes, the class is loaded from the module and returned as
    a type.

    """
    def _try_class(self, stype: str) -> Type:
        """Try to resolve ``stype`` as class."""
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
        return cls

    def map_type(self, stype: str) -> Type:
        tpe: Optional[Type]
        if stype is None:
            tpe = self.default_type
        else:
            tpe = self.data_types.get(stype)
        if tpe is None and self.allow_class:
            try:
                tpe = self._try_class(stype)
            except Exception as e:
                logger.error(f'Could not narrow to class: {stype}: {e}',
                             exc_info=True)
        if tpe is None:
            raise ClassError(f'Non-supported data type: {stype}')
        return tpe


@dataclass(eq=True)
class ClassDoc(object):
    """A meta data for documentation at any level of the class code (methods
    etc).

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
        last_param: List[str] = None
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

    args: Tuple[ClassMethodArg, ...] = field()
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
        """The fully qualified class name."""
        return ClassImporter.full_classname(self.class_type)

    @property
    def is_dataclass(self) -> bool:
        """Whether or not the class is a :class:`dataclasses.dataclass`."""
        return dataclasses.is_dataclass(self.class_type)


@dataclass
class ClassInspector(object):
    """A utility class to return all :class:`dataclasses.dataclass` attribute
    (field) documentation.

    """
    INSPECT_META: ClassVar[str] = 'CLASS_INSPECTOR'
    """Attribute to set to indicate to traverse superclasses as well.  This is
    set as an empty ``dict`` to allow future implementations to filter on what's
    traversed (i.e. ``include_fields``).

    """
    DECORATOR_META: ClassVar[str] = 'CLASS_DECORATOR'
    """Attribute to set which must be a :class:`builtins.dict` with the
    following keys:

      * ``includes``: as a set of decorator names that can be set on methods to
        indicate inclusion on introspected method set.  Otherwise the decorated
        method (such as `@property`) is omitted from the class metadata

    """
    cls: type = field()
    """The class to inspect."""

    attrs: Tuple[str, ...] = field(default=None)
    """The class attributes to inspect, or all found are returned when ``None``.

    """
    data_type_mapper: TypeMapper = field(default=None)
    """The mapper used for narrowing a type from a string parsed from the Python
    AST.

    """
    include_private: bool = field(default=False)
    """Whether to include private methods that start with ``_``."""

    include_init: bool = field(default=False)
    """Whether to include the ``__init__`` method."""

    strict: str = field(default='y')
    """Indicates what to do for undefined or unsupported structures.

    One of:

      * y: raise errors
      * n: ignore
      * w: log as warning
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

    def _map_default(self, item: str, def_node: ast.AST):
        """Map a default from what will be at times an :class:`ast.Name`.  This
        happens when an enum is used as a type, but ``name.id`` only gives the
        enum class name and not the enum value.

        :param item: mapped target string used to create an error message

        :param def_node: the node to map a default

        """
        def map_arg(node):
            if isinstance(node.value, str):
                return f"'{node.value}'"
            else:
                return str(node.value)

        try:
            if isinstance(def_node, ast.Attribute):
                enum_name: str = def_node.attr
                cls: type = self.data_type_mapper.map_type(def_node.value.id)
                if hasattr(cls, '__members__'):
                    default = cls.__members__[enum_name]
                else:
                    msg = f'No default found for class: {cls}.{enum_name}'
                    if self.strict == 'y':
                        raise ClassError(msg)
                    elif self.strict == 'w' and logger.isEnabledFor(
                            logging.WARN):
                        logger.warning(msg)
                    default = None
            elif isinstance(def_node, ast.Constant):
                default = def_node.value
            elif isinstance(def_node, ast.Call):
                func = def_node.func.id
                args = map(map_arg, def_node.args)
                default = f'{func}({", ".join(args)})'
                try:
                    evald = eval(default)
                    default = evald
                except Exception as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'could not invoke: {default}: {e}')
            elif isinstance(def_node, ast.UnaryOp):
                op = def_node.operand
                default = op.value
            elif isinstance(def_node, ast.Name):
                default = self.data_type_mapper.map_type(def_node.id)
            elif hasattr(def_node, 'value'):
                default = def_node.value
            else:
                default = str(def_node)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'default: {default} ({type(default)})/' +
                             f'({type(def_node)})')
            return default
        except Exception as e:
            raise ClassError(f'Could not map {item}: {def_node}: {e}')

    def _get_args(self, node: ast.arguments) -> List[ClassMethodArg]:
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
                    default = self._map_default(f'arg {arg}', defaults[didx])
                    is_positional = False
                if arg.annotation is not None:
                    if isinstance(arg.annotation, ast.Subscript):
                        dtype = arg.annotation.value.id
                    else:
                        dtype = arg.annotation.id
                mtype = self.data_type_mapper.map_type(dtype)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'mapped {name}:{dtype} -> {mtype}, ' +
                                 f'default={default}')
                arg = ClassMethodArg(name, mtype, None, default, is_positional)
            except Exception as e:
                raise ClassError(f'Could not map argument {name}: {e}')
            args.append(arg)
        return args

    def _get_method(self, node: ast.FunctionDef) -> ClassMethod:
        method: ClassMethod = None
        decorators = filter(lambda n: n not in self._decorator_includes,
                            map(lambda n: hasattr(n, 'id') and n.id,
                                node.decorator_list))
        decorators = tuple(decorators)
        name: str = node.name
        is_priv: bool = name.startswith('_')
        is_prop: bool = any(decorators)
        # only public methods (not properties) are parsed for now
        if not is_prop and (self.include_private or not is_priv):
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
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
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

    def _get_inspect_method(self, cls: Type, meth_name: str) -> ClassMethod:
        mems = filter(lambda t: t[0] == meth_name, inspect.getmembers(cls))
        for mem_name, mem in mems:
            sig: Signature = inspect.signature(mem)
            meth_args: List[ClassMethodArg] = []
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                positional = param.kind == Parameter.POSITIONAL_ONLY
                pe = Parameter.empty
                meth_args.append(ClassMethodArg(
                    name=param.name,
                    dtype=None if param.annotation == pe else param.annotation,
                    doc=None,
                    default=None if param.default == pe else param.default,
                    is_positional=positional))
            return ClassMethod(
                name=mem_name,
                doc=inspect.cleandoc(inspect.getdoc(mem)),
                args=tuple(meth_args))

    def _get_class(self, cls: Type) -> Class:
        """Return a dict of attribute (field) to metadata and docstring.

        """
        attrs = self.attrs
        if attrs is None:
            attrs = tuple(filter(lambda i: i[:1] != '_', cls.__dict__.keys()))
        cnode: ast.Node = self._get_class_node()
        fields: List[ClassField] = []
        methods: List[ClassMethod] = []
        for node in cnode.body:
            # parse the dataclass attribute/field defintion
            if isinstance(node, ast.AnnAssign) and \
               isinstance(node.annotation, (ast.Name, ast.Subscript)):
                str_dtype: str
                if isinstance(node.annotation, ast.Name):
                    str_dtype = node.annotation.id
                elif isinstance(node.annotation, ast.Subscript):
                    str_dtype = node.annotation.value.id
                name: str = node.target.id
                dtype: type = self.data_type_mapper.map_type(str_dtype)
                item: str = f"kwarg: '{name}'"
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'mapped dtype {name} {str_dtype} -> {dtype}')
                if node.value is not None and hasattr(node.value, 'keywords'):
                    kwlst: List[ast.keyword] = node.value.keywords
                    kwargs = {k.arg: self._map_default(item, k.value)
                              for k in kwlst}
                    fields.append(ClassField(name, dtype, None, kwargs))
            # parse documentation string right after the dataclass field
            elif (isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Constant) and
                  len(fields) > 0):
                doc = ClassDoc(node.value.value)
                last_field: ClassField = fields[-1]
                if last_field.doc is None:
                    last_field.doc = doc
            elif (isinstance(node, ast.Expr) and
                  len(fields) > 0):
                doc = ClassDoc(node.value.s)
                last_field: ClassField = fields[-1]
                if last_field.doc is None:
                    last_field.doc = doc
            # parse the method
            elif isinstance(node, ast.FunctionDef):
                try:
                    meth = self._get_method(node)
                except Exception as e:
                    raise ClassError(
                        f'could not parse method in {node}', e)
                if meth is not None:
                    methods.append(meth)
            elif isinstance(node, ast.AnnAssign):
                if self.strict == 'w' and logger.isEnabledFor(logging.WARNING):
                    logger.warning(
                        f'assign: {node.target.id}, {node.annotation}')
            else:
                msg = f'not processed node: {type(node)}: {node.value}'
                if self.strict == 'w' and logger.isEnabledFor(logging.WARNING):
                    logger.warning(msg)
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(msg)
        if self.include_init:
            meth = self._get_inspect_method(cls, '__init__')
            if meth is not None:
                methods.append(meth)
        field_dict = OrderedDict()
        meth_dict = OrderedDict()
        for f in fields:
            field_dict[f.name] = f
        for m in methods:
            meth_dict[m.name] = m
        return Class(
            cls,
            None if self.cls.__doc__ is None else ClassDoc(self.cls.__doc__),
            fields=field_dict,
            methods=meth_dict)

    def _get_super_class(self, cls: Type) -> List[Class]:
        """Traverse all superclasses of ``cls``.

        """
        supers = filter(lambda c: c is not object and c is not cls, cls.mro())
        classes = []
        for cls in supers:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'traversing super class: {cls}')
            ci = self.__class__(cls)
            clmeta = ci.get_class()
            classes.append(clmeta)
        return classes

    def get_class(self) -> Class:
        """Return a dict of attribute (field) to metadata and docstring.

        """
        if hasattr(self.cls, self.DECORATOR_META):
            meta: Dict[str, Any] = getattr(self.cls, self.DECORATOR_META)
            self._decorator_includes = meta.get('includes', set())
        else:
            self._decorator_includes = set()
        cls = self._get_class(self.cls)
        if hasattr(self.cls, self.INSPECT_META):
            meta: Dict[str, str] = getattr(self.cls, self.INSPECT_META)
            if not isinstance(meta, dict):
                raise ClassError(
                    f'{self.INSPECT_META} must be a dict in {self.cls}' +
                    f'but got type: {type(meta)}')
            superclasses = self._get_super_class(self.cls)
            superclasses.reverse()
            superclasses.append(cls)
            for sc in superclasses:
                cls.fields.update(sc.fields)
                cls.methods.update(sc.methods)
        return cls
