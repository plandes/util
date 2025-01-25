import unittest
from pathlib import Path
from zensols.util import PackageRequirement, PackageResource


class TestPackage(unittest.TestCase):
    def test_requirement_version_spec(self):
        should_obj = PackageRequirement('frozendict', '1.4.3')
        should_str: str = 'frozendict==1.4.3'
        req = PackageRequirement.from_spec(should_str)
        self.assertEqual('frozendict', req.name)
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

    def test_resource_available(self):
        pr = PackageResource('frozendict')
        self.assertEqual('frozendict', pr.name)
        self.assertTrue(pr.available)
        self.assertTrue(pr.installed)
        self.assertTrue(str(pr).startswith('frozendict=='))
        self.assertEqual(str, type(pr.version))
        self.assertTrue(len(pr.version) > 3)
        pyfile: str = pr.get_path('core.py')
        self.assertTrue(isinstance(pyfile, Path))
        self.assertTrue('frozendict', pyfile.parent.name)

        req = pr.get_package_requirement()
        self.assertEqual('frozendict', req.name)
        self.assertEqual(pr.version, req.version)
        self.assertEqual(req.spec, str(req))
        self.assertRegex(req.spec, r'^frozendict==[0-9.]+$')

    def test_resource_not_installed(self):
        bad_name: str = 'nopkgnada'
        pr = PackageResource(bad_name)
        self.assertEqual(bad_name, pr.name)
        self.assertFalse(pr.available)
        self.assertFalse(pr.installed)
        self.assertEqual(bad_name, str(pr))

    def test_resource_availabe_not_installed(self):
        name: str = 'zensols.util'
        pr = PackageResource(name)
        self.assertEqual(name, pr.name)
        self.assertTrue(pr.available)
        self.assertFalse(pr.installed)
        rpathstr = 'resources/default.conf'
        self.assertEqual(Path(rpathstr), pr[rpathstr])
