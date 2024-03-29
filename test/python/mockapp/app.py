from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
from zensols.persist import Stash
from zensols.config import Dictable, Settings


class Fruit(Enum):
    apple = auto()
    banana = auto()


@dataclass
class TestAction(Dictable):
    """Test command line.

    """
    dry_run: bool = field(default=False)
    """When given don't do anything, just act like it."""

    out_path: Path = field(default=None)
    """The output path."""

    def doit(self, a1, arg0: float, z: Fruit, arg1: int = 1,
             arg2: str = 'str1x', fruit: Fruit = Fruit.banana):
        """Run the test
        command

        in the unit test

        :param a1: first arg doc

        :param arg0: second arg doc

        :param arg1: third arg
                     doc

        :param arg2: forth arg doc

        :param fruit: a tasty selection

        :param z: more selectons

        """
        self.invoke_state = (a1, arg0, arg1, arg2, fruit, z)
        return tuple(list(self.invoke_state) + ['r'])


@dataclass
class TestActionBool(Dictable):
    """A test app with config metadata.

    """
    def action_one(self, opt1: bool = False):
        return 'action1', opt1

    def action2(self, pos1: bool):
        return 'action2', pos1

    def action3(self, opt2: int = None):
        return 'action3', opt2

    def action4(self, pos1: int):
        return 'action4', pos1


@dataclass
class TestActionMeta(Dictable):
    """Test action that contains meta data.

    """
    CLI_META = {'mnemonic_overrides': {'bad_method_name': 'action3',
                                       'another_pythonic_method': 'act4'},
                'mnemonic_excludes': {'good_name'}}

    def good_name(self):
        return 'good'

    def bad_method_name(self, opt1: bool = False):
        return 'bad meth name', opt1

    def another_pythonic_method(self, pos1):
        return 'action2', pos1


@dataclass
class TestActionConfigured(Dictable):
    """A test app to be configured.

    """
    a_stash: Stash

    def do_it(self):
        return 'test app res', tuple(self.a_stash.values())


@dataclass
class TestActionDefault(Dictable):
    """A test app with config metadata.

    """
    def action_one(self, opt1: bool = False):
        return 'action1', opt1

    def action2(self, opt2: int = None):
        return 'action2', opt2


@dataclass
class TestActionOverride(Dictable):
    """Test overriding the command line.

    """
    basket: Settings

    def override_fruit(self):
        """Run the test command"""
        self.invoke_state = (self.basket)
        return self.invoke_state
