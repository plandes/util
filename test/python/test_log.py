import unittest
import logging
from io import StringIO
from zensols.util import LogConfigurer, loglevel

#logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLogConf(unittest.TestCase):
    def test_log(self):
        logger = logging.getLogger('zensols.log.test')
        lconf = LogConfigurer(logger, log_format='%(levelname)s %(message)s',
                              level=logging.INFO)
        buf = lconf.config_buffer()
        logger.info('test123')
        self.assertEqual('INFO test123\n', buf.getvalue())

    def test_out_err(self):
        logger = logging.getLogger('zensols.test.tmp')
        out = StringIO()
        err = StringIO()
        lconf = LogConfigurer(logger, log_format='%(levelname)s %(message)s',
                              level=logging.INFO)
        lconf.config_stream(out, err)
        logger.info('test123')
        logger.warning('warnmsg')
        logger.debug('debugmsg')
        logger.error('err123')
        self.assertEqual('INFO test123\nWARNING warnmsg\n', out.getvalue())
        self.assertEqual('ERROR err123\n', err.getvalue())

    def test_out_err_debug(self):
        logger = logging.getLogger('zensols.test.tmp')
        out = StringIO()
        err = StringIO()
        lconf = LogConfigurer(logger, log_format='%(levelname)s %(message)s',
                              level=logging.DEBUG)
        lconf.config_stream(out, err)
        logger.info('test123')
        logger.warning('warnmsg')
        logger.debug('debugmsg')
        logger.error('err123')
        self.assertEqual('INFO test123\nWARNING warnmsg\nDEBUG debugmsg\n',
                         out.getvalue())
        self.assertEqual('ERROR err123\n', err.getvalue())


class TestLog(unittest.TestCase):
    def tests_with_log(self):
        with loglevel(__name__):
            logger.debug('test')
