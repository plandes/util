from typing import Tuple, Iterable
from enum import Enum, auto
from dataclasses import dataclass, field
import logging
from itertools import chain
from domain import Department, Person

logger = logging.getLogger(__name__)


@dataclass
class EmployeeDatabase(object):
    departments: Tuple[Department]
    high_cost: float

    @property
    def costly_employees(self) -> Iterable[Person]:
        return tuple(filter(lambda e: e.salary > self.high_cost,
                            chain.from_iterable(
                                map(lambda d: d.employees, self.departments))))


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
            if format is Format.short:
                print(dept)
            else:
                dept.write()

    def report_costly(self):
        """Report high salaried employees."""
        emp: Person
        for emp in self.db.costly_employees:
            print(emp)
