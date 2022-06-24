"""Get passwords from the macOS Keychain.app, and optionally add as a
configuraiton.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging
import os
from frozendict import frozendict
from . import DictionaryConfig

logger = logging.getLogger(__name__)


@dataclass
class Keychain(object):
    """A wrapper to macOS's Keychain service using binary ``/usr/bin/security``.
    This provides a cleartext password for the given service and account.

    """
    account: str = field()
    """The account, which is usually an email address."""

    service: str = field(default='python-passwords')
    """the service (grouping in Keychain.app)"""

    @staticmethod
    def getpassword(account: str, service: str) -> str:
        """Get the password for the account and service (see class docs).

        """
        cmd = ('/usr/bin/security find-generic-password ' +
               f'-w -s {service} -a {account}')
        with os.popen(cmd) as p:
            s = p.read().strip()
        return s

    @property
    def password(self):
        """Get the password for the account and service provided as member variables
        (see class docs).

        """
        logger.debug(f'getting password for service={self.service}, ' +
                     f'account={self.account}')
        return self.getpassword(self.account, self.service)


class KeychainConfig(DictionaryConfig):
    """A configuration that adds a user and password based on a macOS Keychain.app
    entry.  The account (user name) and service (a grouping in Keychain.app) is
    provided and the password is fetched.

    Example::

        [import]
        sections = list: keychain_imp

        [keychain_imp]
        type = keychain
        account = my-user-name
        default_section = login
    """
    def __init__(self, account: str, user: str = None,
                 service: str = 'python-passwords',
                 default_section: str = 'keychain'):
        """Initialize.

        :param account: the account (usually an email address) used to fetch in
                        Keychain.app

        :param user: the name of the user to use in the generated entry, which
                     defaults to ``acount``

        :param service: the service (grouping in Keychain.app)

        :param default_section: used as the default section when non given on
                                the get methds such as :meth:`get_option`

        """
        super().__init__(default_section=default_section)
        keychain = Keychain(account, service)
        conf = {self.default_section:
                {'user': account if user is None else user,
                 'password': keychain.password}}
        self._dict_config = frozendict(conf)
