"""Simple string based serialization.

"""
__author__ = 'Paul Landes'

from typing import Dict, Union, Any, Set, Tuple, List
from dataclasses import dataclass, field
import logging
from pprint import pprint
import sys
import json
from json import JSONEncoder
from itertools import chain
from io import TextIOBase
import re
import pkg_resources
from pathlib import Path

logger = logging.getLogger(__name__)
OBJECT_KEYS = {'_type', '_data'}


class PythonObjectEncoder(JSONEncoder):
    def default(self, obj: Any):
        if isinstance(obj, set):
            return {'_type': obj.__class__.__name__, '_data': tuple(obj)}
        return JSONEncoder.default(self, obj)


def as_python_object(dct: Dict[str, str]):
    if set(dct.keys()) == OBJECT_KEYS:
        cls = eval(dct['_type'])
        return cls(dct['_data'])
    return dct


class Settings(object):
    """A default object used to populate in :meth:`.Configurable.populate` and
    :meth:`.ConfigFactory.instance`.

    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def asdict(self) -> Dict[str, Any]:
        return self.__dict__

    def asjson(self, *args, **kwargs) -> str:
        return json.dumps(self.__dict__, *args, **kwargs)

    def get(self, name: str) -> str:
        if hasattr(self, name):
            return getattr(self, name)

    def __eq__(self, other) -> bool:
        return self.__dict__ == other.__dict__

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return self.__str__()

    def write(self, writer: TextIOBase = sys.stdout):
        pprint(self.__dict__, writer)


@dataclass
class Serializer(object):
    """This class is used to parse values in to Python literals and object
    instances in configuration files.

    """
    FLOAT_REGEXP = re.compile(r'^[-+]?\d*\.\d+$')
    INT_REGEXP = re.compile(r'^[-+]?[0-9]+$')
    BOOL_REGEXP = re.compile(r'^True|False')
    PATH_REGEXP = re.compile(r'^path:\s*(.+)$')
    RESOURCE_REGEXP = re.compile(r'^resource(?:\((.+)\))?:\s*(.+)$', re.DOTALL)
    STRING_REGEXP = re.compile(r'^str:\s*(.+)$', re.DOTALL)
    LIST_REGEXP = re.compile(r'^(list|set|tuple)(?:\((.+)\))?:\s*(.+)$', re.DOTALL)
    EVAL_REGEXP = re.compile(r'^(?:eval|dict)(?:\((.+)\))?:\s*(.+)$', re.DOTALL)
    JSON_REGEXP = re.compile(r'^json:\s*(.+)$', re.DOTALL)
    PRIMITIVES = set([bool, float, int, None.__class__])
    DEFAULT_RESOURCE_MODULE = None

    allow_types: Set[type] = field(
        default_factory=lambda:
        set([str, int, float, bool, list, tuple, dict]))
    allow_classes: Tuple[type] = field(default_factory=lambda: (Path,))

    def is_allowed_type(self, value: Any) -> bool:
        if isinstance(value, (tuple, list, set)):
            for i in value:
                if not self.is_allowed_type(i):
                    return False
            return True
        elif isinstance(value, dict):
            for i in chain.from_iterable(value.items()):
                if not self.is_allowed_type(i):
                    return False
            return True
        return value.__class__ in self.allow_types or \
            isinstance(value, self.allow_classes)

    def _parse_eval(self, pconfig: str, evalstr: str = None) -> str:
        if pconfig is not None:
            pconfig = eval(pconfig)
            if 'import' in pconfig:
                imports = pconfig['import']
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'imports: {imports}')
                for i in imports:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'importing: {i}')
                    exec(f'import {i}')
        if evalstr is not None:
            return eval(evalstr)

    def parse_list(self, v: str) -> List[str]:
        """Parse a comma separated list in to a string list.

        Any whitespace is trimmed around the commas.

        """
        if v is None:
            return []
        else:
            return re.split(r'\s*,\s*', v)

    def parse_object(self, v: str) -> Any:
        """Parse as a string in to a Python object.  The following is done to parse the
        string in order:

          1. Primitive (i.e. ``1.23`` is a float, ``True`` is a boolean)
          2. A :class:`pathlib.Path` object when prefixed with ``path:``.
          3. Evaluate using the Python parser when prefixed ``eval:``.
          4. Evaluate as JSON when prefixed with ``json:``.

        """
        if v == 'None':
            v = None
        elif self.FLOAT_REGEXP.match(v):
            v = float(v)
        elif self.INT_REGEXP.match(v):
            v = int(v)
        elif self.BOOL_REGEXP.match(v):
            v = v == 'True'
        else:
            parsed = None
            m = self.STRING_REGEXP.match(v)
            if m:
                parsed = m.group(1)
            if parsed is None:
                m = self.PATH_REGEXP.match(v)
                if m:
                    parsed = Path(m.group(1)).expanduser()
            if parsed is None:
                m = self.LIST_REGEXP.match(v)
                if m:
                    ctype, pconfig, lst = m.groups()
                    parsed = self.parse_list(lst)
                    if pconfig is not None:
                        pconfig = eval(pconfig)
                        tpe = pconfig.get('type')
                        if tpe is not None:
                            tpe = eval(tpe)
                            parsed = list(map(tpe, parsed))
                    if ctype == 'tuple':
                        parsed = tuple(parsed)
                    elif ctype == 'set':
                        parsed = set(parsed)
            if parsed is None:
                m = self.RESOURCE_REGEXP.match(v)
                if m:
                    mod, pathstr = m.groups()
                    if mod is None:
                        if self.DEFAULT_RESOURCE_MODULE is None:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(f'no module path: {pathstr}')
                            parsed = Path(pathstr)
                    if parsed is None:
                        parsed = self.resource_filename(pathstr, mod)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'found resource path: {parsed}')
                        parsed = Path(parsed)
            if parsed is None:
                m = self.EVAL_REGEXP.match(v)
                if m:
                    pconfig, evalstr = m.groups()
                    parsed = self._parse_eval(pconfig, evalstr)
            if parsed is None:
                m = self.JSON_REGEXP.match(v)
                if m:
                    parsed = self._json_load(m.group(1))
            if parsed is not None:
                v = parsed
        return v

    def populate_state(self, state: Dict[str, str],
                       obj: Union[dict, object] = None,
                       parse_types: bool = True) -> Union[dict, object]:
        """Populate an object with at string dictionary.  The keys are used for the
        output, and the values are parsed in to Python objects using
        :meth:`parse_object`.  The keys in the input are used as the same keys
        if ``obj`` is a ``dict``.  Otherwise, set data as attributes on the
        object with :py:func:`setattr`.

        :param state: the data to parse

        :param obj: the object to populate

        """
        obj = Settings() if obj is None else obj
        is_dict = isinstance(obj, dict)
        for k, v in state.items():
            if parse_types and isinstance(v, str):
                v = self.parse_object(v)
            logger.debug('setting {} => {} on {}'.format(k, v, obj))
            if is_dict:
                obj[k] = v
            else:
                setattr(obj, k, v)
        return obj

    def _json_dump(self, data: Any) -> str:
        return json.dumps(data, cls=PythonObjectEncoder)

    def _json_load(self, json_str: str) -> Any:
        return json.loads(json_str, object_hook=as_python_object)

    def format_option(self, obj: Any) -> str:
        """Format a Python object in to the string represetation per object syntax
        rules.

        :see: :meth:`parse_object`

        """
        v = None
        cls = obj.__class__
        if cls == str:
            v = obj
        elif cls in self.PRIMITIVES:
            v = str(obj)
        elif isinstance(obj, Path):
            return f'path: {obj}'
        else:
            v = 'json: ' + self._json_dump(obj)
        return v

    def resource_filename(self, resource_name: str, module_name: str = None):
        """Return a resource based on a file name.  This uses the ``pkg_resources``
        package first to find the resources.  If the resource module does not
        exist, it defaults to the relateve file given in ``module_name``. If it
        finds it, it returns a path on the file system.

        :param: resource_name the file name of the resource to obtain (or name
                if obtained from an installed module)

        :param module_name: the name of the module to obtain the data, which
                            defaults to :obj:`DEFAULT_RESOURCE_MODULE`, which
                            is set by
                            :class:`zensols.cli.simple.SimpleActionCli`

        :return: a path on the file system or resource of the installed module

        """
        if module_name is None:
            module_name = self.DEFAULT_RESOURCE_MODULE
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f'looking resource mod={module_name}{type(module_name)}, ' +
                f'resource={resource_name}{type(resource_name)}')
        res = None
        try:
            if module_name is not None and \
               pkg_resources.resource_exists(module_name, resource_name):
                res = pkg_resources.resource_filename(module_name, resource_name)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'resource exists: {res}')
        except ModuleNotFoundError as e:
            logger.warning(f'could not find module: {e}')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'defaulting to module name: {resource_name}')
            if not res.exists():
                logger.warning(f'could not find path: {resource_name}')
                raise e
        if res is None:
            res = resource_name
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'resolved resource to {res}')
        if not isinstance(res, Path):
            res = Path(res)
        return res
