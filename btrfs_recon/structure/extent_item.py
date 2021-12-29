import construct as cs
from construct_typed import EnumBase, TEnum

from .base import field, Struct

__all__ = [
    'ExtentItemFlags',
    'ExtentItem',
]


class ExtentItemFlags(EnumBase):
    """
    ref: https://btrfs.wiki.kernel.org/index.php/Data_Structures#btrfs_extent_item_flags
    """
    DATA = 0x1
    TREE_BLOCK = 0x2
    FULL_BACKREF = 0x80


class ExtentItem(Struct):
    """
    ref: https://btrfs.wiki.kernel.org/index.php/Data_Structures#btrfs_extent_item
    """
    refs: int = field(cs.Int64ul * 'The number of explicit references to this extent')
    generation: int = field(cs.Int64ul * 'transid of transaction that allocated this extent')
    flags: ExtentItemFlags = field(TEnum(cs.Int8ul, ExtentItemFlags))
