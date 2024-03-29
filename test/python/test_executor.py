from io import StringIO
import sys
import logging
from zensols.util import LogConfigurer, Executor
from logutil import LogTestCase
import time


class TestExecutor(LogTestCase):
    def test_out_err(self):
        logger = logging.getLogger('zensols.test.exec')
        out = StringIO()
        err = StringIO()
        lconf = LogConfigurer(logger, log_format='%(levelname)s %(message)s',
                              level=logging.INFO)
        lconf.config_stream(out, err)
        exe = Executor(logger)
        exe.run('echo stdmsg ; echo errmsg > /dev/stderr')
        time.sleep(.2)
        self.assertEqual('INFO stdmsg\n', out.getvalue())

    def run_sleep_out(self):
        logger = logging.getLogger('zensols.test.exec.sleep')
        lconf = LogConfigurer(logger, log_format='SLEEP OUT: %(levelname)s %(message)s',
                              level=logging.INFO)
        lconf.config_stream(sys.stdout)
        exe = Executor(logger)
        exe.run('echo first ; sleep 1 ; echo second')
