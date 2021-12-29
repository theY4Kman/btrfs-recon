from uuid import UUID

import construct as cs

from . import fields
from .base import field, Struct

__all__ = ['DevItem']


class DevItem(Struct):
    devid: int = field(cs.Int64ul)
    total_bytes: int = field(cs.Int64ul)
    bytes_used: int = field(cs.Int64ul)
    io_align: int = field(cs.Int32ul)
    io_width: int = field(cs.Int32ul)
    sector_size: int = field(cs.Int32ul)
    type: int = field(cs.Int64ul)
    generation: int = field(cs.Int64ul)
    start_offset: int = field(cs.Int64ul)
    dev_group: int = field(cs.Int32ul)
    seek_speed: int = field(cs.Int8ul)
    bandwidth: int = field(cs.Int8ul)
    uuid: UUID = field(fields.UUID)
    fsid: UUID = field(fields.FSID)
