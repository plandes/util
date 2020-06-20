import logging
import unittest
from zensols.persist import Deallocatable, dealloc

logger = logging.getLogger(__name__)


class CorrectImpl(Deallocatable):
    INST = 0

    def __init__(self):
        super().__init__()
        CorrectImpl.INST += 1

    def deallocate(self):
        super().deallocate()
        CorrectImpl.INST -= 1


class TestDealloc(unittest.TestCase):
    def test_dealloc(self):
        Deallocatable.ALLOCATION_TRACKING = True
        self.assertEqual(0, CorrectImpl.INST)
        inst = CorrectImpl()
        self.assertEqual(1, CorrectImpl.INST)
        self.assertEqual(1, len(Deallocatable.ALLOCATIONS))
        self.assertEqual(inst, next(iter(Deallocatable.ALLOCATIONS.values()))[0])
        inst.deallocate()
        self.assertEqual(0, CorrectImpl.INST)
        self.assertEqual(0, len(Deallocatable.ALLOCATIONS))
        Deallocatable.ALLOCATION_TRACKING = False

    def _with_dealloc(self, ret=None):
        with dealloc(CorrectImpl()) as inst:
            self.assertEqual(1, CorrectImpl.INST)
            self.assertEqual(1, len(Deallocatable.ALLOCATIONS))
            self.assertEqual(inst, next(iter(Deallocatable.ALLOCATIONS.values()))[0])
            ret = inst if ret is None else ret
            return ret

    def test_with_dealloc(self):
        Deallocatable.ALLOCATION_TRACKING = True
        self.assertEqual(0, CorrectImpl.INST)
        self.assertEqual(0, len(Deallocatable.ALLOCATIONS))
        obj = self._with_dealloc()
        self.assertEqual(CorrectImpl, type(obj))
        self.assertEqual(0, CorrectImpl.INST)
        self.assertEqual(0, len(Deallocatable.ALLOCATIONS))

        obj = self._with_dealloc(1)
        self.assertEqual(0, CorrectImpl.INST)
        self.assertEqual(0, len(Deallocatable.ALLOCATIONS))
        self.assertEqual(int, type(obj))
        Deallocatable.ALLOCATION_TRACKING = False
