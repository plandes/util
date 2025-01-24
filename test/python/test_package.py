import unittest
from zensols.util import PackageResource


class TestPackage(unittest.TestCase):
    def test_resource(self):
        pr = PackageResource('plac')
        self.assertEqual('plac', pr.name)
        self.assertTrue(pr.exists)
        self.assertEqual(str, type(pr.version))
        self.assertTrue(len(pr.version) > 3)

        req = pr.get_package_requirement()
        self.assertEqual('plac', req.name)
        self.assertEqual(pr.version, req.version)
        self.assertEqual(req.spec, str(req))
        self.assertRegex(req.spec, r'^plac==[0-9.]+$')
