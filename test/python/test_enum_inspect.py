from typing import Dict, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
from zensols.config import Dictable
from zensols.introspect import (
    ClassInspector, Class, ClassMethod, ClassMethodArg, ClassField,
)
from zensols.cli import LogLevel
from logutil import LogTestCase


class Level(Enum):
    debug = auto()
    info = auto()
    warn = auto()


@dataclass
class TestAction(Dictable):
    """Test command line.

    """
    def doit(self, a1, arg0: float, arg1: int = 1, arg2: str = 'str1x'):
        """Run the test
        command

        in the unit test.

        :param a1: first arg doc

        :param arg0: second arg doc

        :param arg1: third arg
                     doc

        :param arg2: fourth arg doc

        """
        print('in do it:', arg1)


@dataclass
class TestActionWithEnum(Dictable):
    """Test command line.

    """
    deflevel: LogLevel = field(default=LogLevel.error)

    def doit(self, a1, arg0: float, arg1: int = 1, arg2: str = 'str1x',
             eparam: LogLevel = LogLevel.debug):
        """Run the test
        command

        in the unit test.

        :param a1: first arg doc

        :param arg0: second arg doc

        :param arg1: third arg
                     doc

        :param arg2: fourth arg doc

        """
        print('in do it:', arg1)


class TestEnumInspect(LogTestCase):
    def test_non_enum(self):
        self.config_logging('zensols.introspect')
        ci = ClassInspector(TestAction)
        cls: Class = ci.get_class()
        self.assertEqual(cls.class_type, TestAction)
        self.assertEqual('Test command line.', cls.doc.text)
        methods = cls.methods
        self.assertEqual({'doit'}, set(methods.keys()))
        method: Dict[str, ClassMethod] = methods['doit']
        self.assertEqual('Run the test command in the unit test.',
                         method.doc.text)
        args: Tuple[ClassMethodArg] = method.args
        self.assertEqual(4, len(args))
        self.assertEqual(('a1', 'arg0', 'arg1', 'arg2'),
                         tuple(map(lambda a: a.name, args)))
        self.assertEqual((str, float, int, str),
                         tuple(map(lambda a: a.dtype, args)))
        self.assertEqual('fourth arg doc', args[3].doc.text)
        self.assertEqual((None, None, 1, 'str1x'),
                         tuple(map(lambda a: a.default, args)))
        self.assertEqual((True, True, False, False),
                         tuple(map(lambda a: a.is_positional, args)))

    def test_enum(self):
        self.config_logging('zensols.introspect')
        ci = ClassInspector(TestActionWithEnum)
        cls: Class = ci.get_class()
        self.assertEqual(cls.class_type, TestActionWithEnum)
        self.assertEqual('Test command line.', cls.doc.text)
        methods = cls.methods
        method: Dict[str, ClassMethod] = methods['doit']
        args: Tuple[ClassMethodArg] = method.args
        self.assertEqual(5, len(args))
        self.assertEqual(('a1', 'arg0', 'arg1', 'arg2', 'eparam'),
                         tuple(map(lambda a: a.name, args)))
        self.assertEqual((str, float, int, str, LogLevel),
                         tuple(map(lambda a: a.dtype, args)))
        self.assertEqual('fourth arg doc', args[3].doc.text)
        self.assertEqual((None, None, 1, 'str1x', LogLevel.debug),
                         tuple(map(lambda a: a.default, args)))
        self.assertEqual((True, True, False, False, False),
                         tuple(map(lambda a: a.is_positional, args)))

        ep: ClassMethodArg = args[-1]
        self.assertEqual('eparam', ep.name)
        self.assertEqual(LogLevel, ep.dtype)
        self.assertEqual(LogLevel.debug, ep.default)

        fields: Tuple[ClassField] = cls.fields
        self.assertEqual({'deflevel'}, set(fields.keys()))
        field = fields['deflevel']
        self.assertEqual('deflevel', field.name)
        self.assertEqual(LogLevel, field.dtype)
        self.assertEqual(LogLevel.error, field.default)
