from typing import Iterable

import construct as cs
from intervaltree import Interval, IntervalTree

from btrfs_recon.types import DevId, PhysicalAddress


class ChunkTreeCache(IntervalTree):
    def insert(
        self,
        logical: int,
        size: int,
        stripes: Iterable[tuple[DevId, PhysicalAddress]] | dict[DevId, PhysicalAddress] | Iterable[cs.Container]
    ) -> Interval:
        """Record a mapping of logical -> physical for a block of logical address space"""
        if not isinstance(stripes, dict):
            stripes = tuple(stripes)
            assert stripes

            if isinstance(stripes[0], cs.Container):
                stripes = {stripe.devid: stripe.offset for stripe in stripes}

        begin = logical
        end = begin + size
        if matches := self[begin:end]:
            assert len(matches) == 1
            ival, = matches
            ival.data.update(stripes)
        else:
            ival = Interval(begin, end, dict(stripes))
            self.add(ival)

        return ival

    def offsets(self, logical: int) -> dict[DevId, PhysicalAddress]:
        """Return the mapped physical addresses for the given logical address

        This method will offset the physical address if the logical address is in the middle of a
        mapped block.
        """
        blocks: set[Interval] = self.at(logical)
        assert len(blocks) <= 1, \
            f'Multiple logical blocks matched {logical}. This should never happen.'

        if not blocks:
            raise KeyError(f'Unable to find physical address mapping for logical address {logical}')

        block = next(iter(blocks))
        offset = logical - block.begin
        return {
            devid: physical_start + offset
            for devid, physical_start in block.data.items()
        }

    def reverse_trees(self) -> dict[DevId, IntervalTree]:
        """Return a tree mapping physical -> logical for each device in the cache"""
        rtrees: dict[DevId, IntervalTree] = {}

        for ival in self.all_intervals:
            for devid, physical in ival.data.items():
                if devid not in rtrees:
                    rtrees[devid] = IntervalTree()
                rtrees[devid].addi(physical, physical + ival.length(), ival.begin)

        return rtrees
