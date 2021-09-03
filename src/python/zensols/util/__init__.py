"""General utility classes to measuring time it takes to do work, to logging
and fork/exec operations.

"""
__author__ = 'Paul Landes'


class APIError(Exception):
    """Base exception from which almost all library raised errors extend.

    """
    pass


from .std import *
from .time import *
from .log import *
from .executor import *
from .pkgres import *
