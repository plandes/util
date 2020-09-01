#!/usr/bin/env python

from pathlib import Path
from zensols.persist import PersistableContainer, PersistedWork, persisted


COUNTER_PATH = Path('counter.dat')


class SomeClass(PersistableContainer):
    def __init__(self, n):
        self.n = n
        self._counter = PersistedWork(COUNTER_PATH, self, mkdir=True)

    @property
    @persisted('_counter')
    def count(self):
        print('return count value')
        return self.n * 2

    @property
    @persisted('_notsaved')
    def notsaved(self):
        print('return unsaved value')
        return self.n * 3


def main():
    inst = SomeClass(5)
    print(inst.count)
    print(inst.count)
    print(inst.notsaved)
    print(inst.notsaved)

    print('creating 10 class')
    inst = SomeClass(10)
    assert inst.count == 10
    print(inst.count)
    print(inst.notsaved)


if __name__ == '__main__':
    if COUNTER_PATH.exists():
        COUNTER_PATH.unlink()
    main()
