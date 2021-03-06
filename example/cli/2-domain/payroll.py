from typing import Tuple
from enum import Enum, auto
from dataclasses import dataclass, field
import logging
from domain import Department

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
        print(f'printing employees using format: {format}')
        dept: Department
        for dept in self.db.departments:
            if format == Format.short:
                print(dept)
            else:
                dept.write()
