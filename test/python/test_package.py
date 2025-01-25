import unittest
from zensols.util import PackageRequirement, PackageResource


class TestPackage(unittest.TestCase):
    def test_requirement_version_spec(self):
        should_obj = PackageRequirement('plac', '1.4.3')
        should_str: str = 'plac==1.4.3'
        req = PackageRequirement.from_spec(should_str)
        self.assertEqual('plac', req.name)
        self.assertEqual('1.4.3', req.version)
        self.assertEqual(should_str, str(req))
        self.assertEqual(should_str, str(should_obj))
        self.assertEqual(should_obj, req)

    def test_requirement_url_spec(self):
        url = 'https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz'
        name: str = 'en_core_sci_sm'
        should_str: str = f'{name} @ {url}'
        req = PackageRequirement.from_spec(should_str)
        self.assertEqual(name, req.name)
        self.assertEqual(None, req.version)
        self.assertEqual(url, req.url)
        self.assertEqual(should_str, str(req))

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
