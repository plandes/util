"""More advanced implementation of an action based command line.

"""
__author__ = 'Paul Landes'

import re
import os
import sys
import logging
import inspect
from pathlib import Path
from functools import reduce
import optparse
from optparse import OptionParser
from configparser import ExtendedInterpolation
from zensols.config import IniConfig
from . import SimpleActionCli

logger = logging.getLogger(__name__)


class PrintActionsOptionParser(OptionParser):
    """Implements a human readable implementation of print_help for action based
    command line handlers (i.e. OneConfPerActionOptionsCli).

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def action_options(self):
        return self._action_options

    @property
    def action_names(self):
        return sorted(self.action_options.keys())

    @action_options.setter
    def action_options(self, opts):
        self._action_options = opts
        self.usage = '%prog <list|{}> [options]'.\
                     format('|'.join(self.action_names))

    def print_help(self, file=sys.stdout):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('print help: %s' % self.invokes)
            logger.debug('action options: %s' % self.action_options)
        OptionParser.print_help(self, file)

        action_name_len = reduce(lambda x, y: max(x, y),
                                 map(lambda x: len(x), self.action_names))
        action_fmt_str = '  {:<' + str(action_name_len) + '}  {}'
        action_help = []
        opt_str_len = 0
        def_str_len = 0
        # format text for each action and respective options
        for action_name in self.action_names:
            if action_name in self.invokes:
                action_doc = self.invokes[action_name][2].capitalize()
                opts = map(lambda x: x['opt_obj'],
                           self.action_options[action_name])
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'{action_name} -> {action_doc}, {opts}')
                opt_strs = []
                for opt in opts:
                    short_opt, long_opt, sep, default = '', '', '', ''
                    if opt._short_opts and len(opt._short_opts) > 0:
                        short_opt = opt._short_opts[0]
                    if opt._long_opts and len(opt._long_opts) > 0:
                        long_opt = opt._long_opts[0]
                    if opt.metavar is not None:
                        otype = f' <{opt.metavar}>'
                    elif opt.type is not None:
                        otype = f' <{opt.type.upper()}>'
                    else:
                        otype = ''
                    if len(short_opt) > 0 and len(long_opt) > 0:
                        sep = ', '
                    opt_str = f'  {short_opt}{sep}{long_opt}{otype}'
                    if opt.default and opt.default != ('NO', 'DEFAULT'):
                        default = str(opt.default)
                    opt_strs.append({'str': opt_str,
                                     'default': default,
                                     'help': opt.help})
                    opt_str_len = max(opt_str_len, len(opt_str))
                    def_str_len = max(def_str_len, len(default))
                action_help.append(
                    {'doc': action_fmt_str.format(action_name, action_doc),
                     'opts': opt_strs})

        opt_str_fmt = '{:<' + str(opt_str_len) + '}  {:<' +\
                      str(def_str_len) + '}  {}\n'

        file.write('Actions:\n')
        for i, ah in enumerate(action_help):
            file.write(ah['doc'] + '\n')
            for op in ah['opts']:
                file.write(opt_str_fmt.format(
                    op['str'], op['default'], op['help']))
            if i < len(action_help) - 1:
                file.write('\n')


class PerActionOptionsCli(SimpleActionCli):
    def __init__(self, *args, **kwargs):
        self.action_options = {}
        super().__init__(*args, **kwargs)

    def _init_executor(self, executor, config, args):
        mems = inspect.getmembers(executor, predicate=inspect.ismethod)
        if 'set_args' in (set(map(lambda x: x[0], mems))):
            executor.set_args(args)

    def _log_config(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('executors: %s' % self.executors)
            logger.debug('invokes: %s' % self.invokes)
            logger.debug('action options: %s' % self.action_options)
            logger.debug('opts: %s' % self.opts)
            logger.debug('manditory opts: %s' % self.manditory_opts)

    def make_option(self, *args, **kwargs):
        return optparse.make_option(*args, **kwargs)

    def _create_parser(self, usage):
        return PrintActionsOptionParser(
            usage=usage, version='%prog ' + str(self.version))

    def _config_parser_for_action(self, args, parser):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('config parser for action: %s' % args)
        action = args[0]
        if action in self.action_options:
            for opt_cfg in self.action_options[action]:
                opt_obj = opt_cfg['opt_obj']
                parser.add_option(opt_obj)
                self.opts.add(opt_obj.dest)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('manditory: %s' % opt_cfg['manditory'])
                if opt_cfg['manditory']:
                    self.manditory_opts.add(opt_obj.dest)
        self._log_config()


class OneConfPerActionOptionsCli(PerActionOptionsCli):
    """Convenience action handler that allows a definition on a per action
    basis.  See the test cases for examples of how to use this as the detail is
    all in the configuration pased to the init method.

    :param opt_config: the option configuration (see project documentation)

    :param config_type: the class used for the configuration and defaults to
                        :class:`zensols.util.configbase.Configurable`.

    """
    def __init__(self, opt_config, config_type=IniConfig, **kwargs):
        self.opt_config = opt_config
        self.config_type = config_type
        super().__init__({}, {}, **kwargs)

    def _config_global(self, oc):
        parser = self.parser
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('global opt config: %s' % oc)
        if 'whine' in oc and oc['whine'] is not None:
            logger.debug('configuring whine option')
            self._add_whine_option(parser, default=oc['whine'])
        if 'short' in oc and oc['short']:
            logger.debug('configuring short option')
            self._add_short_option(parser)
        if 'config_option' in oc:
            conf = oc['config_option']
            self.config_opt_conf = conf
            opt = conf['opt']
            logger.debug('config opt: %s', opt)
            opt_obj = self.make_option(opt[0], opt[1], **opt[3])
            parser.add_option(opt_obj)
            if opt[2]:
                self.manditory_opts.add(opt_obj.dest)
        if 'global_options' in oc:
            for opt in oc['global_options']:
                logger.debug('global opt: %s', opt)
                opt_obj = self.make_option(opt[0], opt[1], **opt[3])
                logger.debug('parser opt: %s', opt_obj)
                parser.add_option(opt_obj)
                self.opts.add(opt_obj.dest)
                if opt[2]:
                    self.manditory_opts.add(opt_obj.dest)

    def _config_executor(self, oc):
        exec_name = oc['name']
        gaopts = self.action_options
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('config opt config: %s' % oc)
        for action in oc['actions']:
            action_name = action['name']
            meth = action['meth'] if 'meth' in action else re.sub(r'[- ]', '_', action_name)
            doc = action['doc'] if 'doc' in action else re.sub(r'[-_]', ' ', meth)
            inv = [exec_name, meth, doc]
            logger.debug('inferred action: %s: %s' % (action, inv))
            self.invokes[action_name] = inv
            if 'opts' not in action:
                action['opts'] = ()
            aopts = gaopts[action_name] if action_name in gaopts else []
            gaopts[action_name] = aopts
            for opt in action['opts']:
                logger.debug('action opt: %s' % opt)
                opt_obj = self.make_option(opt[0], opt[1], **opt[3])
                logger.debug('action opt obj: %s' % opt_obj)
                aopts.append({'opt_obj': opt_obj, 'manditory': opt[2]})
        self.executors[exec_name] = oc['executor']

    def config_parser(self):
        super().config_parser()
        parser = self.parser
        self._config_global(self.opt_config)
        for oc in self.opt_config['executors']:
            self._config_executor(oc)
        parser.action_options = self.action_options
        parser.invokes = self.invokes
        self._log_config()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('finished config parser')

    def _create_config(self, conf_file):
        return self.config_type(config_file=conf_file)

    def _get_default_config(self, params):
        return super().get_config(params)

    def _find_conf_file(self, conf, params):
        conf_name = conf['name']
        conf_file = Path(params[conf_name])
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'config configuration: {conf}, name: {conf_name}, ' +
                         f'params: {params}')
        if conf_file is not None:
            if not conf_file.exists() and \
               ('expect' not in conf or conf['expect']):
                raise IOError('no such configuration file: %s' % conf_file)
        return conf_file

    def get_config(self, params):
        if not hasattr(self, 'config_opt_conf'):
            conf = self._get_default_config(params)
        else:
            conf_def = self.config_opt_conf
            conf_file = self._find_conf_file(conf_def, params)
            if conf_file is None:
                conf = None
            else:
                good_keys = filter(lambda x: params[x] is not None,
                                   params.keys())
                defaults = {k: str(params[k]) for k in good_keys}
                conf = self._create_config(conf_file)
                for k, v in defaults.items():
                    conf.set_option(k, v)
        if conf is None:
            conf = self._get_default_config(params)
        logger.debug('returning config: %s' % conf)
        return conf


class OneConfPerActionOptionsCliEnv(OneConfPerActionOptionsCli):
    """A command line option parser that first parses an ini file and passes that
    configuration on to the rest of the CLI action processing in the super
    class.

    """
    def __init__(self, opt_config, config_env_name=None, no_os_environ=False,
                 *args, **kwargs):
        """Initialize.

        :param opt_config: the option configuration (see project documentation)

        :param config_env_name:
            the name of the environment variable that holds the resource like
            name (i.e. ~/.<program name>rc); this will be used as the
            configuration file if it is given and found; otherwise a
            ``ValueError`` is rasied if not found

        :param no_os_environ:
            if ``True`` do not add environment variables to the configuration
            environment

        """
        super().__init__(opt_config, *args, **kwargs)
        if config_env_name is None:
            self.default_config_file = None
        else:
            conf_env_var = config_env_name.upper()
            if conf_env_var in os.environ:
                cfile = os.environ[conf_env_var]
            else:
                cfile = '~/.{config_env_name}'
            cfile = Path(cfile).expanduser()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'configured default config file: {cfile}')
            self.default_config_file = cfile
        self.no_os_environ = no_os_environ

    def _create_config(self, conf_file):
        conf = super()._create_config(conf_file)
        defs = {}
        if not self.no_os_environ:
            logger.debug(f'adding environment to config: {os.environ}')
            if isinstance(conf, IniConfig) and \
               isinstance(conf.parser._interpolation, ExtendedInterpolation):
                env = {}
                for k, v in os.environ.items():
                    env[k] = v.replace('$', '$$')
            else:
                env = os.environ
            defs.update(env)
        logger.debug('creating with conf_file: {}'.format(conf_file))
        for k, v in defs.items():
            conf.set_option(k, v)
        return conf

    def _find_conf_file(self, conf, params):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('finding config: {}'.format(self.default_config_file))
        if self.default_config_file is None:
            conf_file = super().\
                _find_conf_file(conf, params)
        else:
            conf_name = conf['name']
            conf_file = params[conf_name]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'config: {conf}, name: {conf_name}, ' +
                             f'params: {params}, default_config_file: ' +
                             f'{self.default_config_file}')
            if conf_file is None:
                if os.path.isfile(self.default_config_file):
                    conf_file = self.default_config_file
                elif 'expect' in conf and conf['expect']:
                    if conf_file is None:
                        raise IOError('no configuration file defined in: %s or %s' %
                                      (conf['name'], self.default_config_file))
                    raise IOError('no such configuration file: %s' % conf_file)
        return conf_file
