"""Submodules provide both in memory and on disk persistance.  These include
annotations to provide easy, fast and convenient options to cache expensive to
create data (structures).

"""
__author__ = 'Paul Landes'

from .dealloc import *
from .annotation import *
from .domain import *
from .stash import *
from .composite import *
from .shelve import *
