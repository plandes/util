"""Stash extensions to distribute item creation over multiple processes.

"""
__author__ = 'Paul Landes'

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List, Any, Tuple
import logging
import math
from multiprocessing import Pool
from zensols.util.time import time
from zensols.config import (
    Configurable,
    ImportConfigFactory,
)
from zensols.persist import (
    Stash,
    PreemptiveStash,
    chunks,
)

logger = logging.getLogger(__name__)


class StashMapReducer(object):
    def __init__(self, stash: Stash, n_workers: int = 10):
        self.stash = stash
        self.n_workers = n_workers

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

    def map(self):
        id_sets = self.stash.key_groups(self.key_group_size)
        pool = Pool(self.n_workers)
        return pool.map(self._map_ids, id_sets)

    def __call__(self):
        mapval = self.map()
        reduced = map(self._reduce, mapval)
        return self._reduce_final(reduced)


class FunctionStashMapReducer(StashMapReducer):
    def __init__(self, stash: Stash, func, n_workers: int = 10):
        super().__init__(stash, n_workers)
        self.func = func

    def _map(self, id: str, val):
        return self.func(id, val)

    @staticmethod
    def map_func(*args, **kwargs):
        mr = FunctionStashMapReducer(*args, **kwargs)
        return mr.map()


@dataclass
class ChunkProcessor(object):
    """Represents a chunk of work created by the parent and processed on the child.
    
    :param config: the application context configuration used to create the
                   parent stash
    :param name: the name of the parent stash used to create the chunk, and
                 subsequently process this chunk
    :param chunk_id: the nth chunk
    :param data: the data created by the parent to be processed

    """
    config: Configurable
    name: str
    chunk_id: int
    data: object

    def _create_stash(self):
        return ImportConfigFactory(self.config).instance(self.name)

    def process(self):
        """Create the stash used to process the data, then persisted in the stash.

        """
        stash = self._create_stash()
        cnt = 0
        for id, inst in stash._process(self.data):
            stash.delegate.dump(id, inst)
            cnt += 1
        return cnt

    def __str__(self):
        return f'{self.name}: data: {type(self.data)}'


@dataclass
class MultiProcessStash(PreemptiveStash, metaclass=ABCMeta):
    """A stash that forks processes to process data in a distributed fashion.  The
    stash is typically created by a ``StashFactory`` in the child process.
    Work is chunked (grouped) and then sent to child processes.  In each, a new
    instance of this same stash is created using the ``StashFactory`` and then
    an abstract method is called to dump the data.

    To implement, the ``_create_chunks`` and ``_process`` methods must be
    implemented.

    :param chunk_size: the size of each group of data sent to the child
                       process to be handled; in some cases the child
                       process will get a chunk of data smaller than this
                       (the last) but never more
    :param workers: the number of processes spawned to accomplish the work

    """
    chunk_size: int
    workers: int
 
    @abstractmethod
    def _create_data(self) -> List[Any]:
        """Create data in the parent process to be processed in the child process(es)
        in chunks.

        """
        pass

    @abstractmethod
    def _process(self, chunk: List[Any]) -> Iterable[Tuple[str, Any]]:
        """Process a chunk of data, each created by ``_create_data`` and then grouped.

        """
        pass

    @staticmethod
    def _process_work(chunk: ChunkProcessor) -> int:
        """Process a chunk of data in the child process that was created by the parent
        process.

        """
        return chunk.process()

    def _create_chunk_processor(self, chunk_id: int, data: Any):
        """Factory method to create the ``ChunkProcessor`` instance.

        """
        return ChunkProcessor(self.config, self.name, chunk_id, data)

    def _spawn_work(self) -> int:
        """Chunks and invokes a multiprocessing pool to invokes processing on the
        children.

        """
        data = map(lambda x: self._create_chunk_processor(*x),
                   enumerate(chunks(self._create_data(), self.chunk_size)))
        logger.debug(f'spawning {self.chunk_size} chunks across ' +
                     f'{self.workers} workers')
        with Pool(self.workers) as p:
            with time('processed chunks'):
                cnt = sum(p.map(self.__class__._process_work, data))
        return cnt

    def prime(self):
        """If the delegate stash data does not exist, use this implementation to
        generate the data and process in children processes.

        """
        has_data = self.has_data
        logger.debug(f'asserting data: {has_data}')
        if not has_data:
            with time('spawining work in {self}'):
                self._spawn_work()
            self._reset_has_data()

    def get(self, name: str, default=None):
        self.prime()
        return super().get(name, default)

    def load(self, name: str):
        self.prime()
        return super().load(name)

    def keys(self):
        self.prime()
        return super().keys()
