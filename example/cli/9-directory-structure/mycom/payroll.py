from typing import Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from itertools import chain
from zensols.config import Configurable
from .domain import Department

logger = logging.getLogger(__name__)


@dataclass
class EmployeeDatabase(object):
    departments: Tuple[Department]


class Format(Enum):
    short = auto()
    verbose = auto()


@dataclass
class Tracker(object):
    """Tracks and distributes employee payroll.

    """
    db: EmployeeDatabase = field()
    """An instance not given on the commnd line."""

    dry_run: bool = field(default=False)
    """If given, don't do anything, just act like it."""

    def print_employees(self, format: Format = Format.short):
        """Show all employees.

        :param format: the detail of reporting

        """
        logger.info(f'printing employees using format: {format}')
        dept: Department
        for dept in self.db.departments:
            if format is Format.short:
                print(dept)
            else:
                dept.write()

    def report_salary(self):
        """Report average of employees' salaries.

        """
        logger.info('reporting average salary')
        sals = tuple(map(lambda p: p.salary,
                         chain.from_iterable(
                             map(lambda d: d.employees, self.db.departments))))
        print(f'number employees: {len(sals)}')
        print(f'average salary: ${sum(sals) / len(sals)}')

    def _private_method(self):
        print('will not show up since starts with `_`')

    def stray_method(self):
        print('also will not show up since decorator declares `mnemonics`')


@dataclass
class PackageReporter(object):
    config: Configurable

    def report(self):
        """Print package information."""
        name: str = self.config.get_option('name', section='package')
        print(f'package: {name}')
