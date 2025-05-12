"""Scientific utilities.

"""
__author__ = 'Paul Landes'


class ScientificUtil(object):
    """A class containing utility methods.

    """
    @staticmethod
    def fixed_format(v: float, length: int = 1, add_pad: bool = False) -> str:
        """Format a number to a width resorting to scientific notation where
        necessary.  The returned string is left padded with space in cases where
        scientific notation is too wide for ``v > 0``.  The mantissa is cut off
        also for ``v > 0`` when the string version of the number is too wide.

        :param length: the length of the return string to include as padding

        """
        n: int = length
        ln: int = None
        pad: int = None
        while n > 0:
            i = len('%#.*g' % (n, v))
            s = '%.*g' % (n + n - i, v)
            ln = len(s)
            pad = length - ln
            if pad >= 0:
                break
            n -= 1
        if add_pad and pad > 0:
            s = (' ' * pad) + s
        return s
