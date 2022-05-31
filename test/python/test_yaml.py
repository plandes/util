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
            'project.context.project.aval'))
        eqstr = 'a non-subst ${HOME} but homedir works val'
        self.assertEqual(eqstr, conf.get_option('project.context.litval'))
        eqlist = ['apple', 'banana', 'nlparse orange']
        self.assertEqual(eqlist, conf.get_option('project.fruit'))
        self.assertEqual({'project'}, conf.sections)

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

    def test_yaml_set_sections(self):
        conf = YamlConfig('test-resources/config-sections.yml',
                          sections={'project.template-directory'})
        self.assertEqual('Zensol Python', conf.get_option('project.org_name'))
        self.assertEqual({'project.template-directory'}, conf.sections)

    def test_yaml_set_sections_decl(self):
        conf = YamlConfig('test-resources/config-sections-decl.yml')
        self.assertEqual('Zensol Python', conf.get_option('project.org_name'))
        self.assertEqual({'project.context'}, conf.sections)
        self.assertEqual({'default': 'someproj', 'example': 'nlparse'},
                         conf.populate({}, 'project.context'))

    def test_yaml_level_sections(self):
        conf = YamlConfig('test-resources/config-sections-level.yml')
        should = {'second_tree.st-dir', 'project.context',
                  'project.template-directory'}
        self.assertEqual(should, conf.sections)
