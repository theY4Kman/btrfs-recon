import construct as cs

from .base import field, Struct
from .key import Key, KeyType

__all__ = ['LeafItem']


def _get_data_field():
    from . import (
        InodeItem,
        InodeRef,
        DirItem,
        FileExtentItem,
        RootItem,
        RootRef,
        ExtentItem,
        DevItem,
        ChunkItem,
    )

    key_type_struct_map = {
        KeyType.InodeItem: InodeItem,
        KeyType.InodeRef: InodeRef,
        KeyType.DirItem: DirItem,
        KeyType.ExtentData: FileExtentItem,
        KeyType.RootItem: RootItem,
        KeyType.RootRef: RootRef,
        KeyType.ExtentItem: ExtentItem,
        KeyType.DevItem: DevItem,
        KeyType.ChunkItem: ChunkItem,
    }
    key_type_subcon_map = {
        key: struct.as_struct()
        for key, struct in key_type_struct_map.items()
    }
    return cs.Switch(cs.this.key.ty, key_type_subcon_map)


class LeafItem(Struct):
    key: int = field(Key)
    offset: int = field(cs.Int32ul)
    size: int = field(cs.Int32ul)
    data: int = field(
        cs.Pointer(
            cs.this._.header.phys_end + cs.this.offset,
            cs.LazyBound(_get_data_field),
        )
    )
