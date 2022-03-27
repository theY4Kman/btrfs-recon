from datetime import datetime
from uuid import UUID

import construct as cs
from construct_typed import TEnum

from . import fields
from .base import Struct, field
from .inode import InodeItem
from .key import Key

__all__ = [
    'RootItemFlag',
    'RootItem',
]


class RootItemFlag(fields.EnumBase):
    SUBVOL_RDONLY = (1 << 0)


class RootItem(Struct):
    inode: int = field(InodeItem)
    generation: int = field(cs.Int64ul)
    root_dirid: int = field(cs.Int64ul)
    bytenr: int = field(cs.Int64ul)
    byte_limit: int = field(cs.Int64ul)
    bytes_used: int = field(cs.Int64ul)
    last_snapshot: int = field(cs.Int64ul)
    flags: int = field(TEnum(cs.Int64ul, RootItemFlag))
    refs: int = field(cs.Int32ul)
    drop_progress: Key = field(Key)
    drop_level: int = field(cs.Int8ul)
    level: int = field(cs.Int8ul)
    generation_v2: int = field(cs.Int64ul)
    uuid: UUID = field(fields.UUID)
    parent_uuid: UUID = field(fields.UUID)
    received_uuid: UUID = field(fields.UUID)
    ctransid: int = field(cs.Int64ul, 'updated when an inode changes')
    otransid: int = field(cs.Int64ul, 'trans when created')
    stransid: int = field(cs.Int64ul, 'trans when sent. non-zero for received subvol')
    rtransid: int = field(cs.Int64ul, 'trans when received. non-zero for received subvol')
    ctime: datetime = field(fields.Timespec)
    otime: datetime = field(fields.Timespec)
    stime: datetime = field(fields.Timespec)
    rtime: datetime = field(fields.Timespec)
    reserved: list[int] = field(cs.Int64ul[8])
