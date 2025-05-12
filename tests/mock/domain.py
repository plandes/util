from zensols.persist import ReadOnlyStash


class RangeStash1(ReadOnlyStash):
    def __init__(self, n):
        super(RangeStash1, self).__init__()
        self.n = n
        self.prefix = ''

    def load(self, name: str):
        return f'{self.prefix}{name}'

    def keys(self):
        return map(str, range(self.n))
