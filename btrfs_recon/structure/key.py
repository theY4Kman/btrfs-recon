import construct as cs
from construct_typed import EnumBase, TEnum

from .base import Struct, field

__all__ = [
    'ObjectId',
    'KeyType',
    'Key',
    'KeyPtr',
]


class ObjectId(EnumBase):
    RootTree = 1
    ExtentTree = 2
    ChunkTree = 3
    DevTree = 4
    FsTree = 5
    RootTreeDir = 6
    CsumTree = 7
    QuotaTree = 8
    UuidTree = 9
    FreeSpaceTree = 10
    DevStats = 0
    Balance = -4
    Orphan = -5
    TreeLog = -6
    TreeLogFixup = -7
    TreeReloc = -8
    DataRelocTree = -9
    ExtentCsum = -10
    FreeSpace = -11
    FreeIno = -12
    Multiple = -255
    FirstFree = 256
    LastFree = -256
    FirstChunkTree = 256


class KeyType(EnumBase):
    UNKNOWN = 0

    InodeItem = 1
    InodeRef = 12
    InodeExtref = 13
    InodeXattr = 24
    OrphanItem = 48
    DirLogItem = 60
    DirLogIndex = 72
    DirItem = 84
    DirIndex = 96
    ExtentData = 108
    ExtentCsum = 128
    RootItem = 132
    RootBackref = 144
    RootRef = 156
    ExtentItem = 168
    MetadataItem = 169
    TreeBlockRef = 176
    ExtentDataRef = 178
    ExtentRefV0 = 180
    SharedBlockRef = 182
    SharedDataRef = 184
    BlockGroupItem = 192
    FreeSpaceInfo = 198
    FreeSpaceExtent = 199
    FreeSpaceBitmap = 200
    DevExtent = 204
    DevItem = 216
    ChunkItem = 228
    QgroupStatus = 240
    QgroupInfo = 242
    QgroupLimit = 244
    QgroupRelation = 246
    TemporaryItem = 248
    PersistentItem = 249
    DevReplace = 250
    Subvol = 251
    ReceivedSubvol = 252


class Key(Struct):
    objectid: ObjectId = field(TEnum(cs.Int64ul, ObjectId))
    ty: KeyType = field(TEnum(cs.Int8ul, KeyType))
    offset: int = field(cs.Int64ul)


class KeyPtr(Struct):
    key: Key = field(Key)
    blockptr: int = field(cs.Int64ul)
    generation: int = field(cs.Int64ul)
