#!/usr/bin/env python

from zensols.cli import ApplicationFactory


def main():
    cli = ApplicationFactory('payroll', 'app.conf')
    cli.invoke()


if __name__ == '__main__':
    main()
