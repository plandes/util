import unittest
from zensols.persist import PersistableError, ZipStash


class TestZipStash(unittest.TestCase):
    def test_keys(self):
        stash = ZipStash('test-resources/dconf.zip')
        should = ['dconf/happy/a.conf', 'dconf/happy/b.conf',
                  'dconf/sad/a.conf', 'dconf/sad/b.conf']
        self.assertEqual(should, sorted(stash.keys()))

    def test_exists(self):
        stash = ZipStash('test-resources/dconf.zip')
        self.assertTrue(stash.exists('dconf/happy/a.conf'))
        self.assertTrue(stash.exists('dconf/sad/b.conf'))
        self.assertFalse(stash.exists('a.conf'))

    def test_entries(self):
        stash = ZipStash('test-resources/dconf.zip', encoding='utf-8')
        should = '[default]\nparam1 = 3.14\n'
        self.assertEqual(should, stash.load('dconf/happy/a.conf'))
        self.assertEqual(should, stash.get('dconf/happy/a.conf'))
        self.assertEqual(should, stash['dconf/happy/a.conf'])
        should = '[default]\nparam1 = p1\nparam2 = p2\n'
        self.assertEqual(should, stash.load('dconf/sad/b.conf'))

    def test_bad_root(self):
        with self.assertRaisesRegex(PersistableError, r"^Roots can not start"):
            ZipStash('test-resources/dconf.zip', root='dconf/happy/')

    def test_exists_root(self):
        stash = ZipStash('test-resources/dconf.zip', root='dconf/happy')
        self.assertTrue(stash.exists('a.conf'))
        self.assertTrue(stash.exists('b.conf'))
        self.assertFalse(stash.exists('dconf/sad/b.conf'))

    def test_keys_root(self):
        stash = ZipStash('test-resources/dconf.zip', root='dconf/happy')
        should = ['a.conf', 'b.conf']
        self.assertEqual(should, sorted(stash.keys()))

    def test_entries_root(self):
        stash = ZipStash('test-resources/dconf.zip', root='dconf/happy',
                         encoding='utf-8')
        should = '[default]\nparam1 = 3.14\n'
        self.assertEqual(should, stash.load('a.conf'))
        self.assertEqual(should, stash.get('a.conf'))
        self.assertEqual(should, stash['a.conf'])
