"""Utility classes for command line functionality.

"""
__author__ = 'Paul Landes'

import sys


class DocUtil(object):
    """A utility class to format API documentation parsed from the class.

    """
    @staticmethod
    def normalize(text: str) -> str:
        """Lower case and remove punctuation."""
        doc = text.lower()
        if doc[-1] == '.':
            doc = doc[0:-1]
        return doc

    @staticmethod
    def unnormalize(text: str) -> str:
        """Return a normalized doc string back to a (more) typical English syntax.

        """
        return text[0].upper() + text[1:] + '.'

    @classmethod
    def module_name(cls) -> str:
        """Return the ``config`` (parent) module name."""
        if not hasattr(cls, '_mod_name') is None:
            mname = sys.modules[__name__].__name__
            parts = mname.split('.')
            if len(parts) > 1:
                mname = '.'.join(parts[:-1])
            cls._mod_name = mname
        return cls._mod_name
