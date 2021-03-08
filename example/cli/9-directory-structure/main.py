#!/usr/bin/env python

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


if __name__ == '__main__':
    cli = PayrollApplicationFactory.instance()
    cli.invoke()
