import unittest

from datetime import timedelta
from zensols.util import DurationFormatter


class TestDurationFormatter(unittest.TestCase):
    def test_min_to_hour(self):
        def minutes_to_hour_min_sec(m: int, s: int = None) -> str:
            if s is None:
                td = timedelta(minutes=m)
            else:
                td = timedelta(minutes=m, seconds=s)
            f = DurationFormatter(td)
            return f('hour_min_sec')

        self.assertEqual('0:05:00', minutes_to_hour_min_sec(5))
        self.assertEqual('0:00:08', DurationFormatter(8).format('hour_min_sec'))
        self.assertEqual('0:05:03', minutes_to_hour_min_sec(5, 3))
        self.assertEqual('2:05:03', DurationFormatter(timedelta(hours=2, minutes=5, seconds=3)).format('hour_min_sec'))
        self.assertEqual('2:05:04', DurationFormatter(timedelta(hours=2, minutes=5, seconds=3.5))('hour_min_sec'))
        self.assertEqual('0:10:00', minutes_to_hour_min_sec(10))
        self.assertEqual('0:00:30', minutes_to_hour_min_sec(0.5))
        self.assertEqual('0:01:30', minutes_to_hour_min_sec(1.5))
        self.assertEqual('1:15:30', minutes_to_hour_min_sec(75.5))
        self.assertEqual('1:09:00', minutes_to_hour_min_sec(69))
        self.assertEqual('1:09:54', minutes_to_hour_min_sec(69.9))
        self.assertEqual('1:09:59', minutes_to_hour_min_sec(69.99))
        self.assertEqual('1:10:00', minutes_to_hour_min_sec(69.999))

    def test_min_to_duration(self):
        def minutes_to_duration(m: int, s: int = None) -> str:
            if s is None:
                td = timedelta(minutes=m)
            else:
                td = timedelta(minutes=m, seconds=s)
            f = DurationFormatter(td)
            return f('non_zero')

        self.assertEqual('5m', minutes_to_duration(5))
        self.assertEqual('8s', DurationFormatter(8).format('non_zero'))
        self.assertEqual('10m', minutes_to_duration(10))
        self.assertEqual('30s', minutes_to_duration(0.5))
        self.assertEqual('1m, 30s', minutes_to_duration(1.5))
        self.assertEqual('1h, 15m, 30s', minutes_to_duration(75.5))
        self.assertEqual('1h, 9m', minutes_to_duration(69))
        self.assertEqual('1h, 9m, 54s', minutes_to_duration(69.9))
        self.assertEqual('1h, 9m, 59s', minutes_to_duration(69.99))
        self.assertEqual('1h, 9m', minutes_to_duration(68.999))
