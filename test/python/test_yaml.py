import unittest
from zensols.config import YamlConfig


class TestYaml(unittest.TestCase):
    def test_yaml(self):
        defaults = {'HOME': 'homedir'}
        conf = YamlConfig('test-resources/config-test.yml',
                          delimiter='^',
                          default_vars=defaults)
        single_op = conf.get_option('project.template-directory.default')
        self.assertEqual('make-proj', single_op)
        self.assertEqual('Zensol Python Project', conf.get_option(
            'project.context.project.aval', expect=True))
        eqstr = 'a non-subst ${HOME} but homedir works val'
        self.assertEqual(eqstr, conf.get_option(
            'project.context.litval', expect=True))
        eqlist = ['apple', 'banana', 'nlparse orange']
        self.assertEqual(eqlist, conf.get_option(
            'project.fruit', expect=True))

    def test_yaml_ops(self):
        ops = {'HOME': 'homedir',
               'project.context.envval': 'here',
               'project.context.litval': 'a non-subst ${HOME} but homedir works val',
               'project.context.project.aval': 'Zensol Python Project',
               'project.context.project.default': 'someproj',
               'project.context.project.description': 'github repo name',
               'project.context.project.example': 'nlparse',
               'project.description': 'Simple Clojure project',
               'project.fruit': ['apple', 'banana', 'nlparse orange'],
               'project.name': 'Zensol Python Project',
               'project.org_name': 'Zensol Python',
               'project.template-directory.default': 'make-proj',
               'project.template-directory.description': 'root of source code tree',
               'project.template-directory.example': 'view/template/proj'}
        defaults = {'HOME': 'homedir'}
        conf = YamlConfig('test-resources/config-test.yml',
                          delimiter='^',
                          default_vars=defaults)
        self.assertEqual(ops, conf.options)
