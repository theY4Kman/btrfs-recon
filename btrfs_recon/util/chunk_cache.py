from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

import construct as cs
from intervaltree import Interval, IntervalTree

from btrfs_recon.types import DevId, PhysicalAddress

if TYPE_CHECKING:
    from btrfs_recon import structure


class ChunkTreeCache(IntervalTree):
    def insert(
        self,
        log_start: int,
        log_end: int,
        stripe_len: int,
        stripes: (
            Iterable[tuple[DevId, PhysicalAddress]]
            | dict[DevId, PhysicalAddress]
            | Iterable[cs.Container | structure.Stripe]
        ),
    ) -> Interval:
        """Record a mapping of logical -> physical for a block of logical address space"""
        from btrfs_recon import structure

        if not isinstance(stripes, dict):
            stripes = tuple(stripes)
            assert stripes

            if isinstance(stripes[0], (cs.Container, structure.Stripe)):
                stripes = [(stripe.devid, stripe.offset) for stripe in stripes]

        if matches := self[log_start:log_end]:
            assert len(matches) == 1
            ival, = matches
            ival.data['stripe_len'] = stripe_len
            ival.data['stripes'] = stripes
        else:
            ival = Interval(log_start, log_end, {
                'stripe_len': stripe_len,
                'stripes': stripes,
            })
            self.add(ival)

        return ival

    def offsets(self, logical: int, size: int = 1) -> Iterable[tuple[DevId, PhysicalAddress, int]]:
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

        stripe_len = block.data['stripe_len']
        stripes = block.data['stripes']
        num_stripes = len(stripes)

        log_offset = logical - block.begin
        pre_stripe_units = log_offset // stripe_len
        stripe_offset = log_offset % stripe_len

        while size > 0:
            n_stripe_units = pre_stripe_units // num_stripes
            stripe_idx = pre_stripe_units % num_stripes
            (devid, chunk_phys) = stripes[stripe_idx]

            num_bytes = min(size, stripe_len, stripe_len - stripe_offset)
            phys = chunk_phys + n_stripe_units * stripe_len + stripe_offset
            yield devid, phys, num_bytes

            pre_stripe_units += 1
            stripe_offset = 0
            size -= num_bytes

    def reverse_trees(self) -> dict[DevId, IntervalTree]:
        """Return a tree mapping physical -> logical for each device in the cache"""
        rtrees: dict[DevId, IntervalTree] = {}

        for ival in self.all_intervals:
            for devid, physical in ival.data.items():
                if devid not in rtrees:
                    rtrees[devid] = IntervalTree()
                rtrees[devid].addi(physical, physical + ival.length(), ival.begin)

        return rtrees
