import unittest
from pathlib import Path
from zensols.config import IniConfig


class TestConfigPopulate(unittest.TestCase):
    def setUp(self):
        self.conf = IniConfig('test-resources/populate-test.conf')

    def test_primitive(self):
        s = self.conf.populate()
        self.assertEqual(s.param1, 3.14)
        self.assertEqual(s.param2, 9)
        self.assertEqual(s.param3, 10.1)
        self.assertEqual(s.param4, -10.1)
        self.assertEqual(s.param5, 'dog')
        self.assertEqual(s.param6, True)
        self.assertEqual(s.param7, False)
        self.assertEqual(s.param8, None)

    def test_type(self):
        s = self.conf.populate(section='type_test')
        self.assertEqual(s.str1, 'some string')
        self.assertEqual(s.lst_str, ['1', '2'])
        self.assertEqual(s.lst_int, [1, 2])
        self.assertEqual(s.lst_float, [1., 2.])
        self.assertEqual(s.lst_str2, ['1', '2'])
        self.assertEqual(s.tup_str, ('1', '2'))
        self.assertEqual(s.tup_int, (1, 2))
        self.assertEqual(s.tup_float, (1., 2.))
        self.assertEqual(s.tup_str2, ('1', '2'))
        self.assertEqual(s.set_str2, {'2', '1'})
        self.assertEqual(s.lst_obj, [1, 2, Path('a.txt'), Path('res.txt')])

    def test_eval(self):
        s = self.conf.get_option_object('param9')
        self.assertEqual(s, {'scott': 2, 'paul': 1})
        s = self.conf.get_option_object('param10')
        self.assertEqual(list, type(s))
        self.assertEqual(s, [1, 5, 10])
        self.assertEqual(None, self.conf.get_option_object('param8'))

    def test_eval_populate(self):
        s = self.conf.populate()
        self.assertEqual(dict, type(s.param9))
        self.assertEqual(s.param9, {'scott': 2, 'paul': 1})
        self.assertEqual(list, type(s.param10))
        self.assertEqual(s.param10, [1, 5, 10])

    def test_path(self):
        s = self.conf.populate()
        self.assertTrue(isinstance(s.param11, Path))
        self.assertEqual('/tmp/some/file.txt', str(s.param11.absolute()))

    def test_by_section(self):
        s = self.conf.populate({}, section='single_section')
        self.assertEqual({'car': 'bmw', 'animal': 'dog'}, s)

    def test_eval_import(self):
        counts = tuple(range(3))
        s = self.conf.get_option_object('counts', 'eval_test')
        self.assertEqual(counts, s)
        should = {'car': 'bmw', 'animal': 'dog', 'counts': counts}
        s = self.conf.populate({}, section='eval_test')
        self.assertEqual(should, s)

    def test_json(self):
        dat = self.conf.get_option_object('data', 'json_test')
        self.assertEqual(dat.__class__, list)
        self.assertEqual(3, len(dat))
        self.assertEqual({"animal": "dog", "car": "bmw"}, dat[0])
        self.assertEqual({"somefloat": 1.23, "someint": 5}, dat[1])
        self.assertEqual([5.5, 6.7, True, False], dat[2])
