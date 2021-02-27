from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
from zensols.config import Dictable


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

    def doit(self, a1, arg0: float, arg1: int = 1, arg2: str = 'str1x',
             fruit: Fruit = Fruit.banana):
        """Run the test
        command

        in the unit test

        :param a1: first arg doc

        :param arg0: second arg doc

        :param arg1: third arg
                     doc

        :param arg2: forth arg doc

        """
        self.invoke_state = (a1, arg0, arg1, arg2)
        return tuple(list(self.invoke_state) + ['r'])
