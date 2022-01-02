from enum import IntEnum
from typing import Any, TYPE_CHECKING

import construct as cs
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy.orm as orm

from .base import BaseStruct
from .. import fields

if TYPE_CHECKING:
    from .physical import Device


class BlockGroupFlags(IntEnum):
    DATA = 1 << 0
    SYSTEM = 1 << 1
    METADATA = 1 << 2
    RAID0 = 1 << 3
    RAID1 = 1 << 4
    DUP = 1 << 5
    RAID10 = 1 << 6
    RAID5 = 1 << 7
    RAID6 = 1 << 8
    RAID1C3 = 1 << 9
    RAID1C4 = 1 << 10


class ChunkItem(BaseStruct):
    length = sa.Column(fields.uint8, nullable=False)
    owner = sa.Column(fields.uint8, nullable=False)
    stripe_len = sa.Column(fields.uint8, nullable=False)
    ty = sa.Column(fields.uint8, nullable=False)
    io_align = sa.Column(fields.uint4, nullable=False)
    io_width = sa.Column(fields.uint4, nullable=False)
    sector_size = sa.Column(fields.uint4, nullable=False)
    num_stripes = sa.Column(fields.uint2, nullable=False)
    sub_stripes = sa.Column(fields.uint2, nullable=False)

    stripes = orm.relationship('Stripe', back_populates='chunk_item')

    # TODO (zkanzler): add computed columns for BlockGroupFlags (ty)


class Stripe(BaseStruct):
    chunk_item_id = sa.Column(sa.ForeignKey(ChunkItem.id, ondelete='CASCADE'), nullable=False)
    chunk_item = orm.relationship(ChunkItem)

    devid = sa.Column(fields.uint8, nullable=False)
    offset = sa.Column(fields.uint8, nullable=False)
    dev_uuid = sa.Column(pg.UUID, nullable=False)

    @classmethod
    def parse_struct(cls, device: 'Device', stripe: cs.Container, /) -> dict[str, Any]:
        return {
            **super().parse_struct(device, stripe),
            'devid': stripe.devid,
            'offset': stripe.offset,
            'dev_uuid': stripe.dev_uuid,
        }
