#!/usr/bin/env python

"""This example shows how to use a command-line harness from outside an
application's source directory.  Note that this application would need to
symbolically link to the source's ``resource`` directory if the application was
not installed since it's application configuration sources another resource
(``obj.conf``).  However, the application instead defines it relative to the
application root specifically for this example.

Note the package needs to be installed for this example to work so it can find
this package's resource libraries.

"""

from pathlib import Path
from zensols.cli import CliHarness


def invoke_cli():
    harness = CliHarness(
        root_dir=Path('../cli/10-harness-override').absolute(),
        package_resource='mycom.payroll',
        proto_factory_kwargs={'reload_pattern': r'^mycom\.payroll'},
    )
    return harness.run()


if (__name__ == '__main__'):
    res = invoke_cli()
    df = res.result
    print('department result')
    df.write()
