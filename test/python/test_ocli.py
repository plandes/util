from logutil import LogTestCase
from zensols.cli import ActionCliFactory, ActionCli


class TestActionCli(ActionCli):
    pass


class TestActionObjectCli(LogTestCase):
    def test_cli(self):
        self.config_logging('zensols.cli')
        cli = ActionCliFactory.instance(
            'zensols.testapp', 'test-resources/test_app.conf')
        app = cli.create()
        self.assertTrue(isinstance(app, TestActionCli))
