"""Stash extensions to distribute item creation over multiple processes.

"""
__author__ = 'Paul Landes'

import logging
import math
from multiprocessing import Pool
from zensols.persist import Stash

logger = logging.getLogger(__name__)


class StashMapReducer(object):
    """Process work in sub processes from data in a stash.

    """
    def __init__(self, stash: Stash, n_workers: int = 10):
        self.stash = stash
        self.n_workers = n_workers
        self.pool = None

    @property
    def key_group_size(self):
        n_items = len(self.stash)
        return math.ceil(n_items / self.n_workers)

    def _map(self, id: str, val):
        return (id, val)

    def _reduce(self, vals):
        return vals

    def _reduce_final(self, reduced_vals):
        return reduced_vals

    def _map_ids(self, id_sets):
        return tuple(map(lambda id: self._map(id, self.stash[id]), id_sets))

    def __call__(self):
        id_sets = self.stash.key_groups(self.key_group_size)
        pool = Pool(self.n_workers)
        try:
            mapval = pool.map(self._map_ids, id_sets)
            reduced = map(self._reduce, mapval)
            res = self._reduce_final(reduced)
        finally:
            pool.close()
        return res


class FunctionStashMapReducer(StashMapReducer):
    def __init__(self, stash: Stash, func, n_workers: int = 10):
        super().__init__(stash, n_workers)
        self.func = func

    def _map(self, id: str, val):
        return self.func(id, val)

    @staticmethod
    def map_func(*args, **kwargs):
        reducer = FunctionStashMapReducer(*args, **kwargs)
        return reducer()
