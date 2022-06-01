import unittest
from io import StringIO
from zensols.config import YamlConfig, ImportIniConfig, DictionaryConfig

COND_CONF = """\
[import]
sections = list: imp_yaml

[imp_yaml]
type_map = dict: {'yml': 'condyml'}
config_file = test-resources/config-conditional.yml
"""


class TestYaml(unittest.TestCase):
    def test_env_var(self):
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

    def test_ops(self):
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

    def test_set_sections(self):
        conf = YamlConfig('test-resources/config-sections.yml',
                          sections={'project.template-directory'})
        self.assertEqual('Zensol Python', conf.get_option('project.org_name'))
        self.assertEqual({'project.template-directory'}, conf.sections)

    def test_set_sections_decl(self):
        conf = YamlConfig('test-resources/config-sections-decl.yml')
        self.assertEqual('Zensol Python', conf.get_option('project.org_name'))
        self.assertEqual({'project.context'}, conf.sections)
        self.assertEqual({'default': 'someproj', 'example': 'nlparse'},
                         conf.populate({}, 'project.context'))

    def test_level_sections(self):
        conf = YamlConfig('test-resources/config-sections-level.yml')
        should = {'second_tree.st-dir', 'project.context',
                  'project.template-directory'}
        self.assertEqual(should, conf.sections)

    def _create_cond_config(self, params: dict):
        dconf = DictionaryConfig(params)
        return ImportIniConfig(StringIO(COND_CONF), children=(dconf,))

    def test_condition(self):
        conf = self._create_cond_config({'default': {'testvar': 'True'}})
        self.assertTrue('True', conf.get_option('testvar', 'default'))
        self.assertTrue('glove_50_embedding_layer',
                        conf.get_option('embedding_layer', 'classify_net_settings'))
        should = {'net_settings': 'instance: classify_net_settings',
                  'second_level': {'aval': 1}, 'slcon': 2}
        self.assertTrue(should, conf.populate({}, 'executor'))

        conf = self._create_cond_config({'default': {'testvar': 'eval: 1 == 0'}})
        self.assertTrue('eval: 1 == 0', conf.get_option('testvar', 'default'))
        self.assertTrue('transformer_embedding_layer',
                        conf.get_option('embedding_layer', 'classify_net_settings'))
        should = {'net_settings': 'instance: classify_net_settings',
                  'second_level': {'aval': 2}, 'slcon': 3}
        self.assertTrue(should, conf.populate({}, 'executor'))
