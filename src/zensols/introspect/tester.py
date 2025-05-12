"""Runs test cases from the Python REPL.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
from unittest import main
from unittest.runner import TextTestResult
import sys
import logging
from pathlib import Path
from zensols.introspect import ClassImporter

logger = logging.getLogger(__name__)


@dataclass
class UnitTester(object):
    """A class that runs :mod:`unittest` unit test cases for the rapid
    prototyping use case.  It does this by reloading the unit test case module,
    and then runs it for every invocation of this :class:`typing.Callable`.

    """
    module_name: str = field()
    """The name of the module, which is the Python source file name sans
    extension.

    """
    test_path: Path = field(default=Path('tests'))
    """The path to the source file.  This is added to :obj:`sys.path` if
    non-``None``.

    """
    def run(self) -> TextTestResult:
        """Run all test cases in the module identified by :obj:`module_name`."""
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'running tests in module: {self.module_name}')

        if self.test_path is not None:
            test_path: str = str(self.test_path)
            if test_path not in sys.path:
                sys.path.append(str(test_path))
        ClassImporter.get_module(self.module_name, reload=True)
        test = main(module=self.module_name, exit=False)
        return test.result

    def __call__(self) -> bool:
        """Calls :meth:`run` and returns if it was successful."""
        res: TextTestResult = self.run()
        return res.wasSuccessful()
