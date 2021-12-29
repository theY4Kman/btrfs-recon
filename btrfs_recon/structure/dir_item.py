import construct as cs
from construct_typed import EnumBase, TEnum

from .base import field, Struct
from .key import Key

__all__ = [
    'DirEntryType',
    'DirItem',
]


class DirEntryType(EnumBase):
    Unknown = 0
    RegFile = 1
    Dir = 2
    Chrdev = 3
    Blkdev = 4
    Fifo = 5
    Sock = 6
    Symlink = 7
    Xattr = 8


class DirItem(Struct):
    location: int = field(Key)
    transid: int = field(cs.Int64ul)
    data_len: int = field(cs.Int16ul)
    name_len: int = field(cs.Int16ul)
    ty: DirEntryType = field(TEnum(cs.Int8ul, DirEntryType))
    name: str = field(cs.PaddedString(cs.this.name_len, 'utf8'))
