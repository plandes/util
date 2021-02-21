"""Classes to parse command line arguments.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List
from dataclasses import dataclass, field
import logging
import sys
from io import TextIOBase
from optparse import OptionParser
from zensols.persist import persisted
from zensols.config import Dictable
from . import Option, Action, UsageWriter

logger = logging.getLogger(__name__)


@dataclass
class ArgumentParser(Dictable):
    actions: Tuple[Action]
    top_options: Tuple[Option] = field(default_factory=lambda: [])
    program_name: str = field(default='program')
    version: str = field(default='v0.1')

    def _create_parser(self) -> OptionParser:
        return OptionParser(version='%prog ' + str(self.version))

    def _configure_parser(self, parser: OptionParser):
        for opt in self.top_options:
            op_opt = opt.create_option()
            parser.add_option(op_opt)

    @property
    @persisted('_parser')
    def parser(self) -> OptionParser:
        parser = self._create_parser()
        self._configure_parser(parser)
        return parser

    def write_help(self, writer: TextIOBase = sys.stdout):
        uw = UsageWriter(self.parser, self.actions)
        uw.write(writer=writer)

    def parse(self, args: List[str]):
        parser: OptionParser = self.parser
        (options, args) = parser.parse_args(args)
