from uuid import UUID

import construct as cs
from construct_typed import EnumBase, TEnum

from . import fields
from .base import Struct, field

__all__ = [
    'BlockGroupFlags',
    'Stripe',
    'ChunkItem',
]


class BlockGroupFlags(EnumBase):
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


class Stripe(Struct):
    devid: int = field(cs.Int64ul)
    offset: int = field(cs.Int64ul)
    dev_uuid: UUID = field(fields.UUID)


class ChunkItem(Struct):
    length: int = field(cs.Int64ul)
    owner: int = field(cs.Int64ul)
    stripe_len: int = field(cs.Int64ul)
    ty: int = field(TEnum(cs.Int64ul, BlockGroupFlags))
    io_align: int = field(cs.Int32ul)
    io_width: int = field(cs.Int32ul)
    sector_size: int = field(cs.Int32ul)
    num_stripes: int = field(cs.Int16ul)
    sub_stripes: int = field(cs.Int16ul)
    stripes: int = field(Stripe[cs.this.num_stripes])
