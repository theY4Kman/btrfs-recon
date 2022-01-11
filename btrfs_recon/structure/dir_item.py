import construct as cs
from construct_typed import EnumBase, TEnum

from .base import field, Struct
from .key import Key

__all__ = [
    'DirEntryType',
    'DirItem',
]


class DirEntryType(EnumBase):
    UNKNOWN = 0
    REG_FILE = 1
    DIR = 2
    CHRDEV = 3
    BLKDEV = 4
    FIFO = 5
    SOCK = 6
    SYMLINK = 7
    XATTR = 8


class DirItem(Struct):
    location: Key = field(Key)
    transid: int = field(cs.Int64ul)
    data_len: int = field(cs.Int16ul)
    name_len: int = field(cs.Int16ul)
    ty: DirEntryType = field(TEnum(cs.Int8ul, DirEntryType))
    name: str = field(cs.PaddedString(cs.this.name_len, 'utf8'))
