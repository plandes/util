"""Contains modules that provide configuration utility.

"""
__author__ = 'Paul Landes'


from zensols.util import APIError


class ConfigurationError(APIError):
    """Thrown for any configuration error in this module.

    """
    pass


from .writable import *
from .dictable import *
from .serial import *
from .configbase import *
from .strconfig import *
from .factory import *
from .writeback import *
from .yaml import *
from .iniconfig import *
from .dictconfig import *
from .diff import *
from .json import *
from .configfac import *
from .importini import *
from .importyaml import *
from .envconfig import *
from .keychain import *
from .meta import *
