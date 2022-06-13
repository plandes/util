#!/usr/bin/env python

from zensols.cli import CliHarness


if (__name__ == '__main__'):
    harness = CliHarness(
        package_resource='mycom.payroll',
        proto_factory_kwargs={'reload_pattern': r'^mycom\.payroll'},
    )
    harness.run()
