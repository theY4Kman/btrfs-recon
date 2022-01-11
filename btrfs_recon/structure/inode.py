from datetime import datetime

import construct as cs
from construct_typed import EnumBase, TEnum

from . import fields
from .base import field, Struct

__all__ = [
    'InodeItemFlag',
    'InodeItem',
    'InodeRef',
]


class InodeItemFlag(EnumBase):
    NODATASUM = (1 << 0)
    NODATACOW = (1 << 1)
    READONLY = (1 << 2)
    NOCOMPRESS = (1 << 3)
    PREALLOC = (1 << 4)
    SYNC = (1 << 5)
    IMMUTABLE = (1 << 6)
    APPEND = (1 << 7)
    NODUMP = (1 << 8)
    NOATIME = (1 << 9)
    DIRSYNC = (1 << 10)
    COMPRESS = (1 << 11)


class InodeItem(Struct):
    generation: int = field(cs.Int64ul, 'nfs style generation number')
    transid: int = field(cs.Int64ul, 'transid that last touched this inode')
    size: int = field(cs.Int64ul)
    nbytes: int = field(cs.Int64ul)
    block_group: int = field(cs.Int64ul)
    nlink: int = field(cs.Int32ul)
    uid: int = field(cs.Int32ul)
    gid: int = field(cs.Int32ul)
    mode: int = field(cs.Int32ul)
    rdev: int = field(cs.Int64ul)
    flags: InodeItemFlag = field(TEnum(cs.Int64ul, InodeItemFlag))

    sequence: int = field(cs.Int64ul, 'modification sequence number for NFS')

    reserved: int = field(cs.Int64ul[4])
    atime: datetime = field(fields.Timespec)
    ctime: datetime = field(fields.Timespec)
    mtime: datetime = field(fields.Timespec)
    otime: datetime = field(fields.Timespec)


class InodeRef(Struct):
    index: int = field(cs.Int64ul)
    name_len: int = field(cs.Int16ul)
    name: str = field(cs.PaddedString(cs.this.name_len, 'utf8'))
