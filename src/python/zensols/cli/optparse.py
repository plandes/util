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


class ActionOptionParser(OptionParser):
    """Implements a human readable implementation of print_help for action based
    command line handlers.

    **Implementation note**: we have to extend :class:`~optparser.OptionParser`
    since the ``-h`` option invokes the print help behavior and then exists.

    """
    def __init__(self, actions: Tuple[Action], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usage_writer = UsageWriter(self, actions)

    def print_help(self, file=sys.stdout):
        super().print_help(file)
        self.usage_writer.write(writer=file)


@dataclass
class CommandLineParser(Dictable):
    actions: Tuple[Action]
    top_options: Tuple[Option] = field(default_factory=lambda: [])
    program_name: str = field(default='program')
    version: str = field(default='v0')

    def __post_init__(self):
        if len(self.actions) == 0:
            raise ValueError('must create parser with at least one action')

    def _create_parser(self, actions: Tuple[Action]) -> OptionParser:
        return ActionOptionParser(
            actions, version='%prog ' + str(self.version))

    def _configure_parser(self, parser: OptionParser, options: List[Option]):
        for opt in options:
            op_opt = opt.create_option()
            parser.add_option(op_opt)

    @property
    @persisted('_parser')
    def parser(self) -> ActionOptionParser:
        opts = list(self.top_options)
        actions = self.actions
        if len(self.actions) == 1:
            # TODO: add singleton action doc
            opts.extend(actions[0].options)
            actions = (self.actions[0],)
        parser = self._create_parser(actions)
        self._configure_parser(parser, opts)
        return parser

    def write_help(self, writer: TextIOBase = sys.stdout):
        self.parser.print_help(file=writer)

    def parse(self, args: List[str]):
        parser: OptionParser = self.parser
        (options, args) = parser.parse_args(args)
