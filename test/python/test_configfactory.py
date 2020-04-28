import unittest
import logging
import shutil
from pathlib import Path
from zensols.config import Config
from zensols.persist import (
    ConfigFactory,
    ConfigManager,
    DirectoryStash,
)

logger = logging.getLogger(__name__)


class WidgetFactory(ConfigFactory):
    INSTANCE_CLASSES = {}

    def __init__(self, config):
        super(WidgetFactory, self).__init__(config, '{name}_widget')


class SimpleWidget(object):
    def __init__(self, param1, param2=None):
        logger.debug(f'params: {param1}, {param2}')
        self.param1 = param1
        self.param2 = param2


WidgetFactory.register(SimpleWidget)


class ConfigInitWidget(object):
    def __init__(self, param1, param2=None, config=None, name=None):
        logger.debug(f'params: {param1}, {param2}, config={config}')
        self.param1 = param1
        self.param2 = param2
        self.config = config
        self.name = name


WidgetFactory.register(ConfigInitWidget)


class WidgetManager(ConfigManager):
    INSTANCE_CLASSES = {}
    PATH = Path('target/wmanager')

    def __init__(self, config):
        super(WidgetManager, self).__init__(
            config,
            stash=DirectoryStash(
                path=self.PATH, pattern='{name}_widget_from_mng.dat'),
            pattern='{name}_widget_from_mng',
            default_name='defname')


WidgetManager.register(ConfigInitWidget)


class DataPoint(object):
    INSTANCES = 0

    def __init__(self, id):
        self.id = id
        self.value = id * 2
        self.__class__.INSTANCES += 1

    def __repr__(self):
        return f'({self.id}, {self.value})'


class TestConfigFactory(unittest.TestCase):
    def setUp(self):
        self.config = Config('test-resources/config-factory.conf')
        self.factory = WidgetFactory(self.config)
        self.manager = WidgetManager(self.config)
        targ = Path('target')
        if targ.is_dir():
            shutil.rmtree(targ)
        targ.mkdir()

    def test_simple(self):
        w = self.factory.instance('cool')
        self.assertEqual(3.14, w.param1)
        self.assertEqual(None, w.param2)

    def test_pass_param(self):
        w = self.factory.instance('cool', param2=234)
        self.assertEqual(3.14, w.param1)
        self.assertEqual(234, w.param2)

    def test_pass_param_arg(self):
        w = self.factory.instance('cool_pass', 'p1')
        self.assertEqual('p1', w.param1)
        self.assertEqual('p2', w.param2)

    def test_config_init(self):
        w = self.factory.instance('confi')
        self.assertEqual(3.14, w.param1)
        self.assertEqual(None, w.param2)
        self.assertTrue(isinstance(w.config, Config))
        self.assertEqual('globdef', w.config.get_option('def_param1'))
        self.assertEqual('confi', w.name)

    def test_config_init_pass(self):
        w = self.factory.instance('confi', param2=123.5)
        self.assertEqual(3.14, w.param1)
        self.assertEqual(123.5, w.param2)
        self.assertTrue(isinstance(w.config, Config))
        self.assertEqual('globdef', w.config.get_option('def_param1'))

    def test_config_init_pass_arg(self):
        w = self.factory.instance('confi_pass', 'ip1')
        self.assertEqual('ip1', w.param1)
        self.assertEqual('ip2', w.param2)

    def test_config_mng(self):
        w = self.manager.instance('confi_pass')
        self.assertEqual('ip3', w.param1)
        self.assertFalse(self.manager.exists('one'))
        self.assertEqual(set(), set(self.manager.keys()))
        self.manager.dump('one', 123)
        self.assertEqual(123, self.manager.load('one'))
        self.assertEqual(set(('one',)), set(self.manager.keys()))
