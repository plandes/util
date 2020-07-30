"""Simple string based serialization.

"""
__author__ = 'Paul Landes'

from typing import Dict, Union, Any, Set, Tuple
from dataclasses import dataclass, field
from pprint import pprint
import sys
import json
from json import JSONEncoder
from itertools import chain
import logging
import re
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
    """A default object used to populate in ``Configurable.populate``.

    """
    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()

    def write(self, writer=sys.stdout):
        pprint(self.__dict__, writer)


@dataclass
class Serializer(object):
    FLOAT_REGEXP = re.compile(r'^[-+]?\d*\.\d+$')
    INT_REGEXP = re.compile(r'^[-+]?[0-9]+$')
    BOOL_REGEXP = re.compile(r'^True|False')
    PATH_REGEXP = re.compile(r'^path:\s*(.+)$')
    EVAL_REGEXP = re.compile(r'^eval(?:\((.+)\))?:\s*(.+)$', re.DOTALL)
    JSON_REGEXP = re.compile(r'^json:\s*(.+)$', re.DOTALL)
    PRIMITIVES = set([bool, float, int, None.__class__])

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
                logger.debug(f'imports: {imports}')
                for i in imports:
                    logger.debug(f'importing: {i}')
                    exec(f'import {i}')
        if evalstr is not None:
            return eval(evalstr)

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
            m = self.PATH_REGEXP.match(v)
            if m:
                parsed = Path(m.group(1)).expanduser()
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
        :py:meth:`.parse_object`.  The keys in the input are used as the same
        keys if ``obj`` is a ``dict``.  Otherwise, set data as attributes on
        the object with :py:func:`setattr`.

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

        :see: :py:meth:`.parse_object`

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
