"""Stash extensions to distribute item creation over multiple processes.

"""
__author__ = 'Paul Landes'

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List, Any, Tuple, Callable
import sys
import os
import logging
import math
from multiprocessing import Pool
from zensols.util.time import time
from zensols.config import Configurable, ConfigFactory, ImportConfigFactory
from zensols.persist import (
    Stash, PreemptiveStash, PrimeableStash, chunks, Deallocatable,
)
from zensols.cli import LogConfigurator

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

    def _create_stash(self) -> Tuple[ImportConfigFactory, Any]:
        fac = ImportConfigFactory(self.config)
        with time(f'factory inst {self.name} for chunk {self.chunk_id}',
                  logging.INFO):
            inst = fac.instance(self.name)
            inst.is_child = True
            return fac, inst

    def process(self) -> int:
        """Create the stash used to process the data, then persisted in the stash.

        """
        factory, stash = self._create_stash()
        cnt = 0
        self.config_factory = factory
        stash._init_child(self)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'processing chunk {self.chunk_id} ' +
                        f'with stash {stash.__class__}')
        with time('processed {cnt} items for chunk {self.chunk_id}'):
            for i, (id, inst) in enumerate(stash._process(self.data)):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'dumping {id} -> {inst.__class__}')
                stash.delegate.dump(id, inst)
                Deallocatable._try_deallocate(inst)
                cnt += 1
        Deallocatable._try_deallocate(stash)
        Deallocatable._try_deallocate(factory)
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

    The :obj:`delegate` stash is used to manage the actual persistence of the
    data.

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

    LOG_CONFIG_SECTION = 'multiprocess_log_config'
    """The name of the section to use to configure the log system.  This section
    should be an instance definition of a :class:`.LogConfigurator`.

    """

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
        in chunks.  The returned data is grouped in to sub lists and passed to
        :meth:`_process`.

        :return: an iterable of data to be processed

        """
        pass

    @abstractmethod
    def _process(self, chunk: List[Any]) -> Iterable[Tuple[str, Any]]:
        """Process a chunk of data, each created by ``_create_data`` as a group.

        :param: chunk: a list of data generated by :meth:`_create_data` to be
                       processed in this method

        :return: an iterable of ``(key, data)`` tuples, where ``key`` is used
                 as the string key for the stash and the return value is the
                 data returned by methods like :meth:`load`

        """
        pass

    def _init_child(self, processor: ChunkProcessor):
        """Initialize the child process.

        :param processor: the chunk processor that created this stash in the
                          child process

        """
        self._config_child_logging(processor.config_factory)

    def _config_child_logging(self, factory: ConfigFactory):
        """Initalize the logging system in the child process.

        :param factory: the factory that was used to create this stash and
                        child app configi environment

        """
        warn = None
        config = factory.config
        if config.has_option('section', self.LOG_CONFIG_SECTION):
            conf_sec = config.get_option('section', self.LOG_CONFIG_SECTION)
            if isinstance(factory, ImportConfigFactory):
                log_conf = factory.instance(conf_sec)
                if isinstance(log_conf, LogConfigurator):
                    log_conf.config()
                else:
                    warn = f'unknown configuration object: {type(log_conf)}'
            else:
                warn = f'with unknown factory type: {type(factory)}',
        if warn is not None:
            print(f'warning: can not configure child process logging: {warn}',
                  file=sys.stderr)

    @staticmethod
    def _process_work(processor: ChunkProcessor) -> int:
        """Process a chunk of data in the child process that was created by the parent
        process.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.info(f'processing processor {processor}')
        with time(f'processed processor {processor}'):
            return processor.process()

    def _create_chunk_processor(self, chunk_id: int, data: Any):
        """Factory method to create the ``ChunkProcessor`` instance.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating chunk processor for id {chunk_id}')
        return ChunkProcessor(self.config, self.name, chunk_id, data)

    def _invoke_pool(self, pool: Pool, fn: Callable, data: iter) -> List[int]:
        if pool is None:
            return tuple(map(fn, data))
        else:
            return pool.map(fn, data)

    def _invoke_work(self, workers: int, chunk_size: int,
                     data: Iterable[Any]) -> int:
        fn = self.__class__._process_work
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'{self.name}: spawning work with ' +
                        f'chunk size {chunk_size} across {workers} workers')
        if workers == 1:
            with time('processed chunks'):
                cnt = self._invoke_pool(None, fn, data)
        else:
            with Pool(workers) as p:
                with time('processed chunks'):
                    cnt = self._invoke_pool(p, fn, data)
        return cnt

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
        cnt = self._invoke_work(workers, chunk_size, data)
        return cnt

    def prime(self):
        """If the delegate stash data does not exist, use this implementation to
        generate the data and process in children processes.

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'multi prime, is child: {self.is_child}')
        has_data = self.has_data
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'has data: {has_data}')
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

    def clear(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('clearing')
        super().clear()


@dataclass(init=False)
class MultiProcessFactoryStash(MultiProcessStash):
    """Like :class:`~zensols.persist.FactoryStash`, but uses a subordinate factory
    stash to generate the data in a subprocess(es) in the same manner as the
    super class :class:`.MultiProcessStash`.

    Attributes :obj:`chunk_size` and :obj:`workers` both default to ``0``.

    """

    factory: Stash = field()
    """The stash that creates the data, which is not to be confused with the
    :obj:`delegate`, which persists the data.

    """

    enable_preemptive: bool = field(default=True)
    """If ``False``, do not invoke the :obj:`factory` instance's data
    calculation.

    """

    def __init__(self, config: Configurable, name: str,
                 factory: Stash, enable_preemptive: bool = False,
                 **kwargs):
        """Initialize with attributes :obj:`chunk_size` and :obj:`workers` both
        defaulting to ``0``.

        :param config: the application configuration meant to be populated by
                       :class:`zensols.config.factory.ImportClassFactory`

        :param name: the name of the parent stash used to create the chunk, and
                     subsequently process this chunk

        """
        if 'chunk_size' not in kwargs:
            kwargs['chunk_size'] = 0
        if 'workers' not in kwargs:
            kwargs['workers'] = 0
        super().__init__(config=config, name=name, **kwargs)
        self.factory = factory
        self.enable_preemptive = enable_preemptive

    def _calculate_has_data(self) -> bool:
        has_data = super()._calculate_has_data()
        if not has_data and \
           self.enable_preemptive and \
           isinstance(self.factory, PreemptiveStash):
            has_data = self.factory._calculate_has_data()
        return has_data

    def prime(self):
        if isinstance(self.factory, PrimeableStash):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'priming factory: {self.factory}')
            self.factory.prime()
        super().prime()

    def _create_data(self) -> Iterable[Any]:
        return self.factory.keys()

    def _process(self, chunk: List[Any]) -> Iterable[Tuple[str, Any]]:
        k: str
        for k in chunk:
            if logger.isEnabledFor(logging.DEBUG):
                pid = os.getpid()
                logger.debug(f'processing key {k} in {pid}')
            val: Any = self.factory.load(k)
            yield (k, val)
