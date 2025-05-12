"""Contains modules that provide configuration utility.

"""
__author__ = 'Paul Landes'


from zensols.util import APIError


class ConfigurationError(APIError):
    """Thrown for any configuration error in this module.

    """
    pass

from .dictable import *
from .serial import *
from .configbase import *
from .strconfig import *
from .facbase import *
from .importfac import *
from .writeback import *
from .yaml import *
from .iniconfig import *
from .dictconfig import *
from .diff import *
from .jsonconfig import *
from .configfac import *
from .importyaml import *
from .condyaml import *
from .importini import *
from .envconfig import *
from .treeimpmod import *
from .importtree import *
from .keychain import *
from .meta import *
