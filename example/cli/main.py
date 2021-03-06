#!/usr/bin/env python

from typing import List, Any
from dataclasses import dataclass
from pathlib import Path
from zensols.config import DictionaryConfig
from zensols.cli import ApplicationFactory


@dataclass
class PayrollApplicationFactory(ApplicationFactory):
    @classmethod
    def instance(cls: type, root_dir: Path = Path('.'), *args, **kwargs):
        dconf = DictionaryConfig(
            {'appenv': {'root_dir': str(root_dir)},
             'financial': {'salary': 15.}})
        return cls(package_resource='mycom.payroll', children_configs=(dconf,))


def main(args: List[str] = None) -> Any:
    cli = PayrollApplicationFactory.instance()
    cli.invoke(args)


if __name__ == '__main__':
    args = '--help'.split()
    #args = 'show -c payroll.conf -f verbose'.split()
    #args = '-c payroll.conf -f verbose'.split()
    #args = 'salary -c payroll.conf'.split()
    #args = 'report -c payroll.conf'.split()
    main(args)
