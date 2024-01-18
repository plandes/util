"""A class that allows human readable information (sometimes debugging) output
with a hierarchical structure.

"""
__author__ = 'Paul Landes'

from typing import Union, Any, Iterable, ClassVar, Dict
from abc import ABC, abstractmethod
import sys
import logging
from logging import Logger
import textwrap as tw
from collections import OrderedDict
import itertools as it
from io import TextIOBase, StringIO
from functools import lru_cache
from . import ConfigurationError


@lru_cache(maxsize=50)
def _get_str_space(n_spaces: int) -> str:
    return ' ' * n_spaces


class Writable(ABC):
    """An interface for classes that have multi-line debuging capability.

    .. document private functions
    .. automethod:: _trunc
    .. automethod:: _sp
    .. automethod:: _set_indent
    .. automethod:: _write_line
    .. automethod:: _write_block
    .. automethod:: _write_wrap
    .. automethod:: _write_object
    .. automethod:: _write_iterable
    .. automethod:: _write_dict

    """
    WRITABLE_INDENT_SPACE: ClassVar[int] = 4
    """The default number of spaces to indent each level."""

    WRITABLE_MAX_COL: ClassVar[int] = 80
    """The default maximum column size before wrapping text."""

    WRITABLE_INCLUDE_INDEX: ClassVar[bool] = False
    """Whether to include index numbers with levels in sequences."""

    @classmethod
    def _trunc(cls, s: str, max_len: int = None) -> str:
        max_len = cls.WRITABLE_MAX_COL if max_len is None else max_len
        sl = len(s)
        if sl >= max_len:
            ml = max_len - 3
            s = s[:ml] + '...'
        return s

    def _get_str_space(self, n_spaces: int) -> str:
        return _get_str_space(n_spaces)

    def _sp(self, depth: int) -> str:
        """Utility method to create a space string."""
        indent = getattr(self, '_indent', None)
        indent = self.WRITABLE_INDENT_SPACE if indent is None else indent
        return self._get_str_space(depth * indent)

    def _set_indent(self, indent: int = None):
        """Set the indentation for the instance.  By default, this value is 4.

        :param indent: the value to set as the indent for this instance, or
                       ``None`` to unset it

        """
        self._indent = indent
        _get_str_space.cache_clear()

    def _write_empty(self, writer: TextIOBase, count: int = 1):
        """Write an empty line(s).

        :param count: the number of newlines to add

        """
        writer.write('\n'.join([''] * (count + 1)))

    def _write_line(self, line: str, depth: int, writer: TextIOBase,
                    max_len: Union[bool, int] = False,
                    repl_newlines: bool = False):
        """Write a line of text ``line`` with the correct indentation per
        ``depth`` to ``writer``.

        :param max_line: truncate to the given length if an :class:`int` or
                         :obj:`WRITABLE_MAX_COL` if ``True``

        :repl_newlines: whether to replace newlines with spaces

        """
        s = f'{self._sp(depth)}{line}'
        if repl_newlines:
            s = s.replace('\n', ' ')
        if max_len is True:
            s = self._trunc(s)
        elif max_len is False:
            pass
        elif isinstance(max_len, int):
            s = self._trunc(s, max_len)
        else:
            raise ConfigurationError(
                "Parameter 'max_len' must either be a boolean or integer")
        writer.write(s)
        self._write_empty(writer)

    def _write_divider(self, depth: int, writer: TextIOBase, char: str = '_',
                       width: int = None, header: str = None):
        """Write a text based dividing line (like <hr></hr> in html).

        """
        width = self.WRITABLE_MAX_COL if width is None else width
        width = width - (depth * self.WRITABLE_INDENT_SPACE)
        if header is None:
            line = self._sp(depth) + (char * width)
        else:
            sp = self._sp(depth)
            htext = self._trunc(header, width)
            bar = ('-' * int((width - len(htext)) / 2))
            line = sp + bar + htext + bar
            if (len(htext) % 2) != 0:
                line += '-'
        writer.write(line)
        self._write_empty(writer)

    def _write_wrap(self, text: str, depth: int, writer: TextIOBase,
                    width: int = None, **kwargs):
        """Like :meth:`_write_line` but wrap text per ``width``.

        :param text: the text to word wrap

        :param depth: the starting indentation depth

        :param writer: the writer to dump the content of this writable

        :param width: the width of the text before wrapping, which defaults to
                      :obj:`WRITABLE_MAX_COL`

        :param kwargs: the keyword arguments given to :meth:`textwarp.wrap`

        """
        width = self.WRITABLE_MAX_COL if width is None else width
        lines = tw.wrap(text, width=width, **kwargs)
        self._write_block(lines, depth, writer)

    def _write_block(self, lines: Union[str, Iterable[str]], depth: int,
                     writer: TextIOBase, limit: int = None):
        """Write a block of text with indentation.

        :param limit: the max number of lines in the block to write

        """
        add_ellipses = False
        sp = self._sp(depth)
        if isinstance(lines, str):
            lines = lines.split('\n')
        if limit is not None:
            all_lines = tuple(lines)
            if len(all_lines) > limit:
                add_ellipses = True
                limit -= 1
            lines = it.islice(all_lines, limit)
        for line in lines:
            writer.write(sp)
            writer.write(line)
            self._write_empty(writer)
        if add_ellipses:
            writer.write(sp)
            writer.write('...')
            self._write_empty(writer)

    def _write_object(self, obj: Any, depth: int, writer: TextIOBase):
        """Write an object based on the class of the instance.

        """
        if isinstance(obj, dict):
            self._write_dict(obj, depth, writer)
        elif isinstance(obj, (list, tuple, set)):
            self._write_iterable(obj, depth, writer)
        elif isinstance(obj, _WRITABLE_CLASS):
            obj.write(depth, writer)
        else:
            self._write_line(str(obj), depth, writer)

    def _write_key_value(self, k: Any, v: Any, depth: int, writer: TextIOBase):
        """Write a key value pair from a dictionary.

        """
        sp = self._sp(depth)
        writer.write(f'{sp}{k}: {v}\n')

    def _write_iterable(self, data: Iterable[Any], depth: int,
                        writer: TextIOBase, include_index: bool = None):
        """Write list ``data`` with the correct indentation per ``depth`` to
        ``writer``.

        :param include_index: if ``True``, add an incrementing index for each
                              element in the output

        """
        if include_index is None:
            include_index = self.WRITABLE_INCLUDE_INDEX
        for i, v in enumerate(data):
            if include_index:
                self._write_line(f'i: {i}', depth, writer)
            self._write_object(v, depth + (1 if include_index else 0), writer)

    def _is_container(self, v: Any) -> bool:
        """Return whether or not ``v`` is a container object: ``dict``,
        ``list``, ``tuple`` or a this class.

        """
        return isinstance(v, (dict, list, tuple, _WRITABLE_CLASS))

    def _write_dict(self, data: Dict, depth: int, writer: TextIOBase,
                    inline: bool = False, one_line: bool = False):
        """Write dictionary ``data`` with the correct indentation per ``depth``
        to ``writer``.

        :param data: the data wto write

        :param inline: whether to write values in one line (separate from key)

        :param one_line: whether to print all of ``data`` on one line

        """
        sp = self._sp(depth)
        keys = data.keys()
        if not isinstance(data, OrderedDict):
            keys = sorted(keys)
        if one_line:
            kvs: str = ', '.join(map(lambda t: f'{t[0]}={t[1]}', data.items()))
            writer.write(f'{sp}{kvs}\n')
        else:
            for k in keys:
                v = data[k]
                if not inline and self._is_container(v):
                    writer.write(f'{sp}{k}:\n')
                    self._write_object(v, depth + 1, writer)
                else:
                    self._write_key_value(k, v, depth, writer)

    @abstractmethod
    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Write the contents of this instance to ``writer`` using indention
        ``depth``.

        :param depth: the starting indentation depth

        :param writer: the writer to dump the content of this writable

        """
        pass

    def write_to_log(self, logger: Logger, level: int = logging.INFO,
                     depth: int = 0, split_lines: bool = True):
        """Just like :meth:`write` but write the content to a log message.

        :param logger: the logger to write the message containing content of
                       this writable

        :param level: the logging level given in the :mod:`logging` module

        :param depth: the starting indentation depth

        :param split_lines: if ``True`` each line is logged separately

        """
        if logger.isEnabledFor(level):
            sio = StringIO()
            self.write(depth, sio)
            lines = (sio.getvalue(),)
            if split_lines:
                lines = lines[0].strip().split('\n')
            for line in lines:
                logger.log(level, line)


_WRITABLE_CLASS = Writable
