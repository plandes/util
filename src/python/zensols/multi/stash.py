"""Stash extensions to distribute item creation over multiple processes.

"""
__author__ = 'Paul Landes'

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List, Any, Tuple, Callable
import os
import logging
import math
from multiprocessing import Pool
from zensols.util.time import time
from zensols.config import (
    Configurable,
    ImportConfigFactory,
)
from zensols.persist import (
    PreemptiveStash,
    PrimeableStash,
    chunks,
    Deallocatable,
)

logger = logging.getLogger(__name__)


@dataclass
class ChunkProcessor(object):
    """Represents a chunk of work created by the parent and processed on the child.

    """
    config: Configurable = field()
    """The application context configuration used to create the parent stash.

    """

    name: str = field()
    """The name of the parent stash used to create the chunk, and subsequently
    process this chunk.

    """

    chunk_id: int = field()
    """The nth chunk."""

    data: object = field()
    """The data created by the parent to be processed."""

    def _create_stash(self):
        fac = ImportConfigFactory(self.config)
        with time(f'factory inst {self.name} for chunk {self.chunk_id}',
                  logging.INFO):
            inst = fac.instance(self.name)
            inst.is_child = True
            return fac, inst

    def process(self):
        """Create the stash used to process the data, then persisted in the stash.

        """
        factory, stash = self._create_stash()
        cnt = 0
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'processing chunk {self.chunk_id} ' +
                        f'with stash {stash.__class__}')
        with time('processed {cnt} items for chunk {self.chunk_id}'):
            for i, (id, inst) in enumerate(stash._process(self.data)):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'dumping {id} -> {inst.__class__}')
                stash.delegate.dump(id, inst)
                del inst
                cnt += 1
        Deallocatable._try_deallocate(stash)
        Deallocatable._try_deallocate(factory)
        #gc.collect()
        return cnt

    def __str__(self):
        data = self.data
        if data is not None:
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            dtype = data.__class__.__name__
        else:
            dtype = 'None'
        return f'{self.name} ({self.chunk_id}): data: {dtype}'


@dataclass
class MultiProcessStash(PreemptiveStash, PrimeableStash, metaclass=ABCMeta):
    """A stash that forks processes to process data in a distributed fashion.  The
    stash is typically created by a
    :class:`zensols.config.factory.ImportConfigFactory` in the child process.
    Work is chunked (grouped) and then sent to child processes.  In each, a new
    instance of this same stash is created using :class:`.ImportConfigFactory`
    and then an abstract method is called to dump the data.

    This implemetation of :meth:`prime` is to fork processes to accomplish the
    work.

    The :meth:`_create_data` and :meth:`_process` methods must be
    implemented.

    .. document private functions
    .. automethod:: _create_data
    .. automethod:: _process
    .. automethod:: _process_work
    .. automethod:: _create_chunk_processor

    :see: :class:`zensols.config.factory.ImportConfigFactory`

    """
    ATTR_EXP_META = ('chunk_size', 'workers')

    config: Configurable = field()
    """The application configuration meant to be populated by
    :class:`zensols.config.factory.ImportClassFactory`."""

    name: str = field()
    """The name of the instance in the configuration."""

    chunk_size: int = field()
    """The size of each group of data sent to the child process to be handled;
    in some cases the child process will get a chunk of data smaller than this
    (the last) but never more; if this number is 0, then evenly divide the work
    so that each worker takes the largets amount of work to minimize the number
    of chunks (in this case the data is tupleized).

    """

    workers: int = field()
    """The number of processes spawned to accomplish the work; if this is a
    negative number, add the number of CPU processors with this number, so -1
    would result in one fewer works utilized than the number of CPUs, which is
    a good policy for a busy server.

    """

    def __post_init__(self):
        super().__post_init__()
        if self.workers < 1:
            self.workers = os.cpu_count() + self.workers
        self.is_child = False

    @abstractmethod
    def _create_data(self) -> Iterable[Any]:
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
        if logger.isEnabledFor(logging.DEBUG):
            logger.info(f'processing chunk {chunk}')
        with time(f'processed chunk {chunk}'):
            return chunk.process()

    def _create_chunk_processor(self, chunk_id: int, data: Any):
        """Factory method to create the ``ChunkProcessor`` instance.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating chunk processor for id {chunk_id}')
        return ChunkProcessor(self.config, self.name, chunk_id, data)

    def _invoke_pool(self, pool: Pool, fn: Callable, data: iter) -> int:
        return pool.map(fn, data)

    def _spawn_work(self) -> int:
        """Chunks and invokes a multiprocessing pool to invokes processing on the
        children.

        """
        chunk_size, workers = self.chunk_size, self.workers
        if workers < 1:
            workers = os.cpu_count() + workers
        data = self._create_data()
        if chunk_size < 1:
            data = tuple(data)
            chunk_size = math.ceil(len(data) / workers)
        data = map(lambda x: self._create_chunk_processor(*x),
                   enumerate(chunks(data, chunk_size)))
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'{self.name}: spawning work with ' +
                        f'chunk size {chunk_size} across {workers} workers')
        with Pool(workers) as p:
            with time('processed chunks'):
                cnt = self._invoke_pool(p, self.__class__._process_work, data)
        return cnt

    def prime(self):
        """If the delegate stash data does not exist, use this implementation to
        generate the data and process in children processes.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'multi prime, is child: {self.is_child}')
        has_data = self.has_data
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'asserting data: {has_data}')
        if not has_data:
            with time('completed work in {self.__class__.__name__}'):
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
