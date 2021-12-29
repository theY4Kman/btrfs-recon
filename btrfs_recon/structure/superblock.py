from uuid import UUID

import construct as cs
from construct_typed import EnumBase, TEnum

from btrfs_recon.constants import BTRFS_CSUM_SIZE, BTRFS_LABEL_SIZE, BTRFS_MAGIC

from . import fields
from .base import Struct, field
from .chunk_item import ChunkItem
from .dev_item import DevItem
from .key import Key

__all__ = [
    'SuperblockFlags',
    'SysChunk',
    'Superblock',
]


class SuperblockFlags(EnumBase):
    ERROR = 1 << 2
    SEEDING = 1 << 32
    METADUMP = 1 << 33
    METADUMP_V2 = 1 << 34
    CHANGING_FSID = 1 << 35
    CHANGING_FSID_V2 = 1 << 36


class SysChunk(Struct):
    key: Key = field(Key)
    chunk: ChunkItem = field(ChunkItem)


class Superblock(Struct):
    csum: bytes = field(cs.Hex(cs.Bytes(BTRFS_CSUM_SIZE)))
    fsid: UUID = field(fields.FSID)
    bytenr: int = field(cs.Int64ul)
    flags: SuperblockFlags = field(TEnum(cs.Int64ul, SuperblockFlags))
    magic: str = field(cs.Const(BTRFS_MAGIC))
    generation: int = field(cs.Int64ul)

    #: Logical address of the root tree root
    root: int = field(cs.Int64ul)
    #: Logical address of the chunk tree root
    chunk_root: int = field(cs.Int64ul)
    #: Logical address of the log tree root
    log_root: int = field(cs.Int64ul)
    log_root_transid: int = field(cs.Int64ul)

    total_bytes: int = field(cs.Int64ul)
    bytes_used: int = field(cs.Int64ul)
    root_dir_objectid: int = field(cs.Int64ul)
    num_devices: int = field(cs.Int64ul)
    sector_size: int = field(cs.Int32ul)
    node_size: int = field(cs.Int32ul)
    #: Unused and must be equal to `nodesize`
    leafsize: int = field(cs.Int32ul)
    stripesize: int = field(cs.Int32ul)
    sys_chunk_array_size: int = field(cs.Int32ul)
    chunk_root_generation: int = field(cs.Int64ul)
    compat_flags: int = field(cs.Int64ul)
    compat_ro_flags: int = field(cs.Int64ul)
    incompat_flags: int = field(cs.Int64ul)
    csum_type: int = field(cs.Int16ul)
    root_level: int = field(cs.Int8ul)
    chunk_root_level: int = field(cs.Int8ul)
    log_root_level: int = field(cs.Int8ul)
    dev_item: DevItem = field(DevItem.as_struct())
    label: str = field(cs.PaddedString(BTRFS_LABEL_SIZE, 'utf8'))
    cache_generation: int = field(cs.Int64ul)
    uuid_tree_generation: int = field(cs.Int64ul)
    metadata_uuid: UUID = field(fields.UUID)
    #: Future expansion
    _reserved: int = field(cs.Int64ul[28])
    sys_chunks: list = field(SysChunk[1])
