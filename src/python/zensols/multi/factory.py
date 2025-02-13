"""Stash implementations that use existing factory stashes.

"""
__author__ = 'Paul Landes'

from typing import Iterable, List, Any, Tuple, Union, Type
from dataclasses import dataclass, field
import os
import logging
from zensols.config import Configurable
from zensols.persist import Stash, PreemptiveStash, PrimeableStash
from .stash import MultiProcessor, MultiProcessStash, PoolMultiProcessor

logger = logging.getLogger(__name__)


@dataclass
class MultiProcessDefaultStash(MultiProcessStash):
    """Just like :class:`.MultiProcessStash`, but provide defaults as a
    convenience.

    """
    chunk_size: int = field(default=0)
    """The size of each group of data sent to the child process to be handled;
    in some cases the child process will get a chunk of data smaller than this
    (the last) but never more; if this number is 0, then evenly divide the work
    so that each worker takes the largets amount of work to minimize the number
    of chunks (in this case the data is tupleized).

    """
    workers: Union[int, float] = field(default=1)
    """The number of processes spawned to accomplish the work or 0 to use all
    CPU cores.  If this is a negative number, add the number of CPU processors
    with this number, so -1 would result in one fewer works utilized than the
    number of CPUs, which is a good policy for a busy server.

    If the number is a float, then it is taken to be the percentage of the
    number of processes.  If it is a float, the value must be in range (0, 1].

    """
    processor_class: Type[MultiProcessor] = field(default=PoolMultiProcessor)
    """The class of the processor to use for the handling of the work."""


@dataclass(init=False)
class MultiProcessFactoryStash(MultiProcessDefaultStash):
    """Like :class:`~zensols.persist.domain.FactoryStash`, but uses a
    subordinate factory stash to generate the data in a subprocess(es) in the
    same manner as the super class :class:`.MultiProcessStash`.

    Attributes :obj:`chunk_size` and :obj:`workers` both default to ``0``.

    """
    factory: Stash = field()
    """The stash that creates the data, which is not to be confused with the
    :obj:`delegate`, which persists the data.

    """
    enable_preemptive: Union[str, bool] = field()
    """If ``False``, do not invoke the :obj:`factory` instance's data
    calculation.  If the value is ``always``, then always assume the data is not
    calcuated, which forces the factory prime.  Otherwise, if ``None``, then
    call the super class data calculation falling back on the :obj:`factory` if
    the super returns ``False``.

    """
    def __init__(self, config: Configurable, name: str, factory: Stash,
                 enable_preemptive: bool = False, **kwargs):
        """Initialize with attributes :obj:`chunk_size` and :obj:`workers` both
        defaulting to ``0``.

        :param config: the application configuration meant to be use by a
                       :class:`~zensols.config.importfac.ImportConfigFactory`

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
        has_data = False
        if self.enable_preemptive != 'always':
            has_data = super()._calculate_has_data()
            if not has_data and \
               self.enable_preemptive and \
               isinstance(self.factory, PreemptiveStash):
                has_data = self.factory._calculate_has_data()
        return has_data

    def prime(self):
        if isinstance(self.factory, PrimeableStash):
            if logger.isEnabledFor(logging.DEBUG):
                self._debug(f'priming factory: {self.factory}')
            self.factory.prime()
        super().prime()

    def _create_data(self) -> Iterable[Any]:
        return self.factory.keys()

    def _process(self, chunk: List[Any]) -> Iterable[Tuple[str, Any]]:
        k: str
        for k in chunk:
            if logger.isEnabledFor(logging.INFO):
                pid: int = os.getpid()
                logger.info(f'processing key {k} in process {pid}')
            val: Any = self.factory.load(k)
            yield (k, val)
