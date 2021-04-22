"""A simple straight forward CLI implementation used for the first phase
command line parsing.  More advanced INI (etc) configuration is optionally, and
usually used down stream.

"""
__author__ = 'Paul Landes'

import logging
import sys
import os
from optparse import OptionParser
from pkg_resources import get_distribution, DistributionNotFound
from zensols.util import APIError
from zensols.config import Serializer

logger = logging.getLogger(__name__)


class ActionCliError(APIError):
    """Thrown for all command line interface errors."""
    pass


class SimpleActionCli(object):
    """A simple action based command line interface.

    .. document private functions
    .. automethod:: _config_logging
    .. automethod:: _config_log_level

    """
    def __init__(self, executors, invokes, config=None, version='none',
                 pkg_dist=None, opts=None, manditory_opts=None,
                 environ_opts=None, default_action=None):
        """Construct.

        :param dict executors:
            keys are executor names and values are
            function that create the executor handler instance

        :param dict invokes:
            keys are names of in executors and values are
            arrays with the form: [<option name>, <method name>, <usage doc>]

        :param config: an instance of `zensols.config.Config`

        :param str version: the default version of this command line module,
                            which is overrided by the package's version if it
                            exists

        :param pkg_dist: the name of the module (i.e. zensols.actioncli)

        :param set opts: options to be parsed

        :param set manditory_opts: options that must be supplied in the command

        :param set environ_opts:
            options to add from environment variables; each are upcased to
            be match and retrieved from the environment but are lowercased in
            the results param set

        :param str default_action: the action to use if non is
                                   specified (if any)

        """
        opts = opts if opts else set([])
        manditory_opts = manditory_opts if manditory_opts else set([])
        environ_opts = environ_opts if environ_opts else set([])
        self.executors = executors
        self.invokes = invokes
        self.opts = opts
        self.manditory_opts = manditory_opts
        self.environ_opts = environ_opts
        self.version = version
        self.add_logging = False
        self.config = config
        self.default_action = default_action
        self.pkg = None
        self.pkg_dist = pkg_dist
        if pkg_dist is not None:
            try:
                self.pkg = get_distribution(pkg_dist)
                self.version = self.pkg.version
                Serializer.DEFAULT_RESOURCE_MODULE = pkg_dist
            except DistributionNotFound:
                pass
        if config is not None:
            config.pkg = self.pkg

    def _config_logging(self, level: int):
        """Configure logging by calling :meth:`_config_log_level`, which in turns
        invokes :meth:`.logging.basicConfig`.

        """
        if level == 0:
            levelno = logging.WARNING
        elif level == 1:
            levelno = logging.INFO
        elif level == 2:
            levelno = logging.DEBUG
        if level <= 1:
            fmt = '%(message)s'
        else:
            fmt = '%(levelname)s:%(asctime)-15s %(name)s: %(message)s'
        self._config_log_level(fmt, levelno)

    def _config_log_level(self, fmt: str, levelno: int):
        """Configure logging by calling :meth:`.logging.basicConfig` with the base
        package set at ``levelno`` if available.  In this case, the default
        logging level is set to :obj:`logging.WARNING`.  Otherwise, reconfigure
        logging using a ``levelno`` across all loggers.

        """
        if self.pkg is not None:
            logging.basicConfig(format=fmt, level=logging.WARNING)
            logging.getLogger(self.pkg.project_name).setLevel(level=levelno)
        elif self.pkg_dist is not None:
            logging.basicConfig(format=fmt, level=logging.WARNING)
            logging.getLogger(self.pkg_dist).setLevel(level=levelno)
        else:
            root = logging.getLogger()
            map(root.removeHandler, root.handlers[:])
            logging.basicConfig(format=fmt, level=levelno)
            root.handlers[0].setFormatter(logging.Formatter(fmt))
            root.setLevel(levelno)

    def print_actions(self, short):
        if short:
            for (name, action) in self.invokes.items():
                print(name)
        else:
            pad = max(map(lambda x: len(x), self.invokes.keys())) + 2
            fmt = '%%-%ds %%s' % pad
            for (name, action) in self.invokes.items():
                print(fmt % (name, action[2]))

    def _add_whine_option(self, parser, default=0):
        parser.add_option('-w', '--whine', dest='whine', metavar='NUMBER',
                          type='int', default=default,
                          help='add verbosity to logging')
        self.add_logging = True

    def _add_short_option(self, parser):
        parser.add_option('-s', '--short', dest='short',
                          help='short output for list', action='store_true')

    def _parser_error(self, msg):
        self.parser.error(msg)

    def _default_environ_opts(self):
        opts = {}
        for opt in self.environ_opts:
            opt_env = opt.upper()
            if opt_env in os.environ:
                opts[opt] = os.environ[opt_env]
        logger.debug('default environment options: %s' % opts)
        return opts

    def _init_executor(self, executor, config, args):
        pass

    def get_config(self, params):
        return self.config

    def _config_parser_for_action(self, args, parser):
        pass

    def config_parser(self):
        pass

    def _init_config(self, config):
        if config is not None and \
           self.pkg is not None \
           and hasattr(self, 'pkg'):
            config.pkg = self.pkg

    def _create_parser(self, usage):
        return OptionParser(usage=usage, version='%prog ' + str(self.version))

    def create_executor(self, args=sys.argv[1:]):
        usage = '%prog <list|...> [options]'
        parser = self._create_parser(usage)
        self.parser = parser
        self.config_parser()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'configured parser: {parser}')
        if len(args) > 0 and args[0] in self.invokes:
            logger.debug('configuring parser on action: %s' % args[0])
            self._config_parser_for_action(args, parser)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'parsing arguments: {args}')
        (options, args) = parser.parse_args(args)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('options: <%s>, args: <%s>' % (options, args))
        self.parsed_options = options
        self.parsed_args = args
        if len(args) > 0:
            action = args[0]
        else:
            if self.default_action is None:
                self._parser_error('missing action mnemonic')
            else:
                logger.debug('using default action: %s' % self.default_action)
                action = self.default_action
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('adding logging')
        if self.add_logging:
            self._config_logging(options.whine)
        if action == 'list':
            short = hasattr(options, 'short') and options.short
            self.print_actions(short)
            return None, None
        else:
            if action not in self.invokes:
                self._parser_error("no such action: '%s'" % action)
            (exec_name, meth, _) = self.invokes[action]
            logging.debug('exec_name: %s, meth: %s' % (exec_name, meth))
            params = vars(options)
            config = self.get_config(params)
            self._init_config(config)
            def_params = config.options if config else {}
            def_params.update(self._default_environ_opts())
            for k, v in params.items():
                if v is None and k in def_params:
                    params[k] = def_params[k]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('before filter: %s' % params)
            params = {k: params[k] for k in params.keys() & self.opts}
            for opt in self.manditory_opts:
                if opt not in params or params[opt] is None:
                    self._parser_error('missing option: %s' % opt)
            if config:
                params['config'] = config
            try:
                exec_obj = self.executors[exec_name](params)
                self._init_executor(exec_obj, config, args[1:])
                return meth, exec_obj
            except ActionCliError as err:
                self._parser_error(format(err))

    def invoke(self, args=sys.argv[1:]):
        """Entry point invoked, usually called from ``main``.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logging.debug(f'invoking with args: {args}')
        meth, exec_obj = self.create_executor(args)
        if exec_obj is not None:
            try:
                logging.debug('invoking: %s.%s' % (exec_obj, meth))
                getattr(exec_obj, meth)()
            except ActionCliError as err:
                self._parser_error(format(err))
