import unittest
import logging
from dataclasses import dataclass
from pathlib import Path
import shutil
from zensols.config import (
    Config,
    ImportConfigFactory,
)
from zensols.persist import (
    DelegateStash,
    FactoryStash,
    ReadOnlyStash,
)

logger = logging.getLogger(__name__)


class RangeStashThisMod(ReadOnlyStash):
    def __init__(self, n):
        super(RangeStashThisMod, self).__init__()
        self.n = n
        self.prefix = ''

    def load(self, name: str):
        return f'{self.prefix}{name}'

    def keys(self):
        return map(str, range(self.n))


@dataclass
class RangeHolder(object):
    some_range: object


class TestStashFactory(unittest.TestCase):
    def setUp(self):
        self.conf = Config('test-resources/stash-factory.conf')
        self.target_path = Path('target')
        if self.target_path.exists():
            shutil.rmtree(self.target_path)

    def test_create_same_module(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range3_stash')
        self.assertTrue(isinstance(inst, RangeStashThisMod))
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(6))), set(inst))
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'pf{x}'), range(6))), set(inst))

    def test_create_external(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range1_stash')
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(5))), set(inst))
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'pf{x}'), range(5))), set(inst))

    def test_create_external2(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range5_stash')
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(7))), set(inst))
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'pf{x}'), range(7))), set(inst))

    def test_delegate_create(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range2_stash')
        self.assertFalse(self.target_path.exists())
        self.assertTrue(isinstance(inst, FactoryStash))
        self.assertEqual(set(map(lambda x: (str(x), str(x)), range(5))), set(inst))
        self.assertTrue(self.target_path.is_dir())
        inst.prefix = 'pf'
        self.assertEqual(set(map(lambda x: (str(x), f'{x}'), range(5))), set(inst))

    def test_instance_param(self):
        fac = ImportConfigFactory(self.conf)
        inst = fac.instance('range_holder')
        self.assertTrue(isinstance(inst, RangeHolder))
        arange = inst.some_range
        self.assertTrue(isinstance(arange, RangeStashThisMod))
        self.assertEqual(123, arange.n)
