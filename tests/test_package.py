from typing import Tuple
from dataclasses import FrozenInstanceError
import unittest
import sys
from pathlib import Path
from zensols.util import (
    PackageError, PackageRequirement, PackageResource, PackageManager
)


class TestPackageResource(unittest.TestCase):
    def setUp(self):
        self.req = PackageRequirement('frozendict', '1.4.3')
        self.maxDiff = sys.maxsize

    def test_req_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.req.name = 'nada'

    def test_req_version_spec(self):
        should_obj = self.req
        should_str: str = 'frozendict==1.4.3'
        req = PackageRequirement.from_spec(should_str)
        self.assertEqual('frozendict', req.name)
        self.assertEqual('1.4.3', req.version)
        self.assertEqual(should_str, str(req))
        self.assertEqual(should_str, str(should_obj))
        self.assertEqual(should_obj, req)

    def test_req_url_spec(self):
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

    def test_resource_to_requirement(self):
        pr = PackageResource('frozendict')
        req = pr.to_package_requirement()
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
        self.assertTrue(pr.installed)
        rpathstr = 'resources/default.conf'
        path = str(pr[rpathstr])
        self.assertTrue(path.endswith('resources/default.conf'),
                        f'bad path: {path}')


class TestPackageManagerFind(unittest.TestCase):
    def setUp(self):
        self.spec = 'frozendict==1.2.3'

    def _test_fd_req(self, req: PackageRequirement):
        self.assertEqual(self.spec, str(req))
        self.assertEqual(req.name, 'frozendict')
        self.assertEqual(req.version, '1.2.3')
        self.assertEqual(req.version_constraint, '==')
        self.assertEqual(req.url, None)

    def _test_sci_req(self, req: PackageRequirement):
        self.assertEqual('scispacy~=0.5.3', str(req))
        self.assertEqual(req.name, 'scispacy')
        self.assertEqual(req.version, '0.5.3')
        self.assertEqual(req.version_constraint, '~=')
        self.assertEqual(req.url, None)

    def _test_model_req(self, req: PackageRequirement, url: str, name: str,
                        file_name: str):
        spec = f'{name} @ {url}'
        self.assertEqual(spec, str(req))
        self.assertEqual(req.name, name)
        self.assertEqual(req.version, None)
        self.assertEqual(req.version_constraint, None)
        self.assertEqual(req.url, url)
        self.assertEqual('test-resources/req', str(req.source.parent))
        self.assertEqual(file_name, req.source.name)

    def _test_model_md_req(self, req: PackageRequirement, file_name: str):
        url = 'https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_md-0.5.3.tar.gz'
        name = 'en_core_sci_md'
        self._test_model_req(req, url, name, file_name)

    def _test_model_sm_req(self, req: PackageRequirement):
        url = 'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.6.0/en_core_web_sm-3.6.0-py3-none-any.whl'
        name = 'en-core-web-sm'
        self._test_model_req(req, url, name, 'model.txt')

    def _test_model_bio_req(self, req: PackageRequirement):
        url = 'https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_ner_bionlp13cg_md-0.5.3.tar.gz'
        name = 'en_ner_bionlp13cg_md'
        self._test_model_req(req, url, name, 'model.txt')

    def test_parse_req_string(self):
        mng = PackageManager()
        reqs: Tuple[PackageRequirement, ...] = mng.find_requirements([self.spec])
        self.assertEqual(tuple, type(reqs))
        self.assertEqual(1, len(reqs))
        self._test_fd_req(reqs[0])

    def test_parse_req_file(self):
        nada_name: str = 'nadapkg'
        nada_req = PackageRequirement.from_spec(nada_name)
        mng = PackageManager()
        reqs: Tuple[PackageRequirement, ...] = mng.find_requirements(
            [self.spec, nada_req, Path('test-resources/req/scispacy.txt')])
        self.assertEqual(tuple, type(reqs))
        self.assertEqual(4, len(reqs))
        self._test_model_md_req(reqs[0], 'scispacy.txt')
        self._test_fd_req(reqs[1])
        self.assertEqual(nada_name, reqs[2].name)
        self.assertEqual(None, reqs[2].version)
        self.assertEqual(None, reqs[2].url)
        self._test_sci_req(reqs[3])

    def test_parse_req_dir(self):
        mng = PackageManager()
        reqs: Tuple[PackageRequirement, ...] = mng.find_requirements(
            [self.spec, Path('test-resources/req')])
        self.assertEqual(tuple, type(reqs))
        self.assertEqual(6, len(reqs))
        self._test_model_sm_req(reqs[0])
        self._test_model_md_req(reqs[1], 'model.txt')
        self._test_model_md_req(reqs[2], 'scispacy.txt')
        self._test_model_bio_req(reqs[3])
        self._test_fd_req(reqs[4])
        self._test_sci_req(reqs[5])

    def test_parse_non_req(self):
        mng = PackageManager()
        with self.assertRaises(PackageError):
            mng.find_requirements(
                [Path('test-resources/config-test.conf')])


class TestPackageManagerResolve(unittest.TestCase):
    def test_get_intalled(self):
        mng = PackageManager()
        req: PackageRequirement = mng.get_installed_requirement('frozendict')
        self.assertTrue(isinstance(req, PackageRequirement))
        self.assertEqual('frozendict', req.name)
        self.assertTrue(len(req.version) > 3)
        self.assertTrue(req.meta is not None)
        self.assertTrue(len(req.meta) > 5)

    def test_get_not_intalled(self):
        mng = PackageManager()
        res = mng.get_installed_requirement('nada')
        self.assertEqual(None, res)


class TestPackageManagerInstall(unittest.TestCase):
    def test_pip_command(self):
        pname: str = 'pip-install-test'
        install_req = PackageRequirement.from_spec(pname)
        mng = PackageManager()
        try:
            req: PackageRequirement = mng.get_installed_requirement(pname)
            self.assertEqual(None, req)
            mng.install(install_req)
            req = mng.get_installed_requirement(pname)
            self.assertTrue(req is not None)
            self.assertEqual('pip-install-test', req.name)
            self.assertTrue(len(req.version) > 0, 'version set')
        finally:
            try:
                mng.uninstall(install_req)
            except Exception:
                pass
        req = mng.get_installed_requirement(pname)
        self.assertEqual(None, req)
