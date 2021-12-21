import uuid
from datetime import datetime

import construct as cs

from btrfs_recon.constants import (
    BTRFS_CSUM_SIZE,
    BTRFS_FSID_SIZE,
    BTRFS_LABEL_SIZE,
    BTRFS_MAGIC,
    BTRFS_UUID_SIZE,
)


class UUIDAdapter(cs.Adapter):
    def _decode(self, obj, context, path) -> uuid.UUID:
        return uuid.UUID(bytes=bytes(obj))

    def _encode(self, obj: uuid.UUID, context, path) -> bytes:
        return obj.bytes if context.swapped else obj.bytes_le


UUID = UUIDAdapter(cs.Int8ul[BTRFS_UUID_SIZE])
FSID = UUIDAdapter(cs.Int8ul[BTRFS_FSID_SIZE])


KeyType = cs.Enum(
    cs.Int8ul,
    InodeItem=1,
    InodeRef=12,
    InodeExtref=13,
    InodeXattr=24,
    OrphanItem=48,
    DirLogItem=60,
    DirLogIndex=72,
    DirItem=84,
    DirIndex=96,
    ExtentData=108,
    ExtentCsum=128,
    RootItem=132,
    RootBackref=144,
    RootRef=156,
    ExtentItem=168,
    MetadataItem=169,
    TreeBlockRef=176,
    ExtentDataRef=178,
    ExtentRefV0=180,
    SharedBlockRef=182,
    SharedDataRef=184,
    BlockGroupItem=192,
    FreeSpaceInfo=198,
    FreeSpaceExtent=199,
    FreeSpaceBitmap=200,
    DevExtent=204,
    DevItem=216,
    ChunkItem=228,
    QgroupStatus=240,
    QgroupInfo=242,
    QgroupLimit=244,
    QgroupRelation=246,
    TemporaryItem=248,
    PersistentItem=249,
    DevReplace=250,
)


DirEntryType = cs.Enum(
    cs.Int8ul,
    Unknown=0,
    RegFile=1,
    Dir=2,
    Chrdev=3,
    Blkdev=4,
    Fifo=5,
    Sock=6,
    Symlink=7,
    Xattr=8,
)


ObjectId = cs.Enum(
    cs.Int64ul,
    RootTree=1,
    ExtentTree=2,
    ChunkTree=3,
    DevTree=4,
    FsTree=5,
    RootTreeDir=6,
    CsumTree=7,
    QuotaTree=8,
    UuidTree=9,
    FreeSpaceTree=10,
    DevStats=0,
    Balance=-4,
    Orphan=-5,
    TreeLog=-6,
    TreeLogFixup=-7,
    TreeReloc=-8,
    DataRelocTree=-9,
    ExtentCsum=-10,
    FreeSpace=-11,
    FreeIno=-12,
    Multiple=-255,
    FirstFree=256,
    LastFree=-256,
    FirstChunkTree=256,
    # DevItems=1,
    # BtreeInode=1,
    # EmptySubvolDir=2,
)

CsumType = cs.Enum(
    cs.Int16ul,
    crc32=0,
    xxhash=1,
    sha256=2,
    blake2=3,
)


class Struct(cs.Struct):
    def __init__(self, *subcons, **subconskw):
        super().__init__("LOC" / cs.Hex(cs.Tell), *subcons, **subconskw)


Key = Struct(
    "objectid" / ObjectId,
    "ty" / KeyType,
    "offset" / cs.Int64ul,
    )


Stripe = Struct(
    "devid" / cs.Int64ul,
    "offset" / cs.Int64ul,
    "dev_uuid" / UUID,
    )


BlockGroupFlags = cs.FlagsEnum(
    cs.Int64ul,
    DATA=(1 << 0),
    SYSTEM=(1 << 1),
    METADATA=(1 << 2),
    RAID0=(1 << 3),
    RAID1=(1 << 4),
    DUP=(1 << 5),
    RAID10=(1 << 6),
    RAID5=(1 << 7),
    RAID6=(1 << 8),
    RAID1C3=(1 << 9),
    RAID1C4=(1<< 10),
)


ChunkItem = Struct(
    "length" / cs.Int64ul,
    "owner" / cs.Int64ul,
    "stripe_len" / cs.Int64ul,
    "ty" / BlockGroupFlags,
    "io_align" / cs.Int32ul,
    "io_width" / cs.Int32ul,
    "sector_size" / cs.Int32ul,
    "num_stripes" / cs.Int16ul,
    "sub_stripes" / cs.Int16ul,
    "stripes" / Stripe[cs.this.num_stripes],
    )


SysChunk = Struct(
    "key" / Key,
    "chunk" / ChunkItem,
    )

Header = Struct(
    "csum" / cs.Hex(cs.Bytes(BTRFS_CSUM_SIZE)),
    "fsid" / FSID,
    "bytenr" / cs.Int64ul,
    "flags" / cs.Int64ul,
    "chunk_tree_uuid" / UUID,
    "generation" / cs.Int64ul,
    "owner" / cs.Int64ul,
    "nritems" / cs.Int32ul,
    "level" / cs.Int8ul,
    "end_pos" / cs.Tell,
    )


KeyPtr = Struct(
    "key" / Key,
    "blockptr" / cs.Int64ul,
    "generation" / cs.Int64ul,
    )


Item = Struct(
    "key" / Key,
    "offset" / cs.Int32ul,
    "size" / cs.Int32ul,
    "data" / cs.Pointer(
        cs.this._.header.end_pos + cs.this.offset,
        cs.LazyBound(
            lambda: cs.Switch(cs.this.key.ty, {
                KeyType.InodeItem: InodeItem,
                KeyType.InodeRef: InodeRef,
                KeyType.DirItem: DirItem,
                KeyType.ExtentData: ExtentData,
                KeyType.RootItem: RootItem,
                KeyType.RootRef: RootRef,
                KeyType.ExtentItem: ExtentItem,
                KeyType.DevItem: DevItem,
                KeyType.ChunkItem: ChunkItem,
            }),
        ),
        )
)


TreeNode = Struct(
    "header" / Header,
    "items" / cs.IfThenElse(
        cs.this.header.level == 0,
        Item[cs.this.header.nritems],
        KeyPtr[cs.this.header.nritems],
        ),
    )


TimespecStruct = Struct(
    "sec" / cs.Int64ul,
    "nsec" / cs.Int32ul,
    )


class TimespecDatetimeAdapter(cs.Adapter):
    def _decode(self, obj, context, path):
        try:
            return datetime.utcfromtimestamp(obj.sec).replace(microsecond=int(obj.nsec / 1000))
        except (ValueError, OverflowError, OSError):
            return obj


Timespec = TimespecDatetimeAdapter(TimespecStruct)


InodeItemFlags = cs.FlagsEnum(
    cs.Int64ul,
    NODATASUM=(1 << 0),
    NODATACOW=(1 << 1),
    READONLY=(1 << 2),
    NOCOMPRESS=(1 << 3),
    PREALLOC=(1 << 4),
    SYNC=(1 << 5),
    IMMUTABLE=(1 << 6),
    APPEND=(1 << 7),
    NODUMP=(1 << 8),
    NOATIME=(1 << 9),
    DIRSYNC=(1 << 10),
    COMPRESS=(1 << 11),
)


InodeItem = Struct(
    # nfs style generation number
    "generation" / cs.Int64ul,
    # transid that last touched this inode
    "transid" / cs.Int64ul,
    "size" / cs.Int64ul,
    "nbytes" / cs.Int64ul,
    "block_group" / cs.Int64ul,
    "nlink" / cs.Int32ul,
    "uid" / cs.Int32ul,
    "gid" / cs.Int32ul,
    "mode" / cs.Int32ul,
    "rdev" / cs.Int64ul,
    "flags" / InodeItemFlags,

    # modification sequence number for NFS
    "sequence" / cs.Int64ul,

    "reserved" / cs.Int64ul[4],
    "atime" / Timespec,
    "ctime" / Timespec,
    "mtime" / Timespec,
    "otime" / Timespec,
    )


InodeRef = Struct(
    "index" / cs.Int64ul,
    "name_len" / cs.Int16ul,
    "name" / cs.PaddedString(cs.this.name_len, 'utf8')
)


DirItem = Struct(
    "location" / Key,
    "transid" / cs.Int64ul,
    "data_len" / cs.Int16ul,
    "name_len" / cs.Int16ul,
    "ty" / DirEntryType,
    "name" / cs.PaddedString(cs.this.name_len, 'utf8')
)


CompressionType = cs.Enum(
    cs.Int8ul,
    none=0,
    zlib=1,
    LZO=2,
)
EncryptionType = cs.Enum(
    cs.Int8ul,
    none=0,
)
EncodingType = cs.Enum(
    cs.Int16ul,
    none=0,
)
ExtentDataType = cs.Enum(
    cs.Int8ul,
    inline=0,
    regular=1,
    prealloc=2,
)


# ref: https://btrfs.wiki.kernel.org/index.php/On-disk_Format#EXTENT_DATA_.286c.29
ExtentData = Struct(
    # XXX: are these names canonical?
    "generation" / cs.Int64ul,
    "size" / cs.Int64ul,
    "compression" / CompressionType,
    "encryption" / EncryptionType,
    "encoding" / EncodingType,
    "type" / ExtentDataType,
    "data" / cs.If(cs.this.type == ExtentDataType.inline, cs.HexDump(cs.Bytes(cs.this.size))),
    "ref" / cs.If(cs.this.type != ExtentDataType.inline, cs.Struct(
        "bytenr" / cs.Int64ul * 'logical address of extent. If this is zero, the extent is sparse and consists of all zeroes.',
        "size" / cs.Int64ul * 'size of extent',
        "offset" / cs.Int64ul * 'offset within the extent',
        "data_len" / cs.Int64ul * 'logical number of bytes in file',
        )),
    )


# ref: https://btrfs.wiki.kernel.org/index.php/Data_Structures#btrfs_extent_item_flags
ExtentItemFlags = cs.FlagsEnum(
    cs.Int64ul,
    DATA=0x1,
    TREE_BLOCK=0x2,
    FULL_BACKREF=0x80,
)


# ref: https://btrfs.wiki.kernel.org/index.php/Data_Structures#btrfs_extent_item
ExtentItem = Struct(
    "refs" / cs.Int64ul * 'The number of explicit references to this extent',
    "generation" / cs.Int64ul * 'transid of transaction that allocated this extent',
    "flags" / ExtentItemFlags,
    )


RootItem = Struct(
    "inode" / InodeItem,
    "generation" / cs.Int64ul,
    "root_dirid" / cs.Int64ul,
    "bytenr" / cs.Int64ul,
    "byte_limit" / cs.Int64ul,
    "bytes_used" / cs.Int64ul,
    "last_snapshot" / cs.Int64ul,
    "flags" / cs.Int64ul,
    "refs" / cs.Int32ul,
    "drop_progress" / Key,
    "drop_level" / cs.Int8ul,
    "level" / cs.Int8ul,
    "generation_v2" / cs.Int64ul,
    "uuid" / UUID,
    "parent_uuid" / UUID,
    "received_uuid" / UUID,
    # updated when an inode changes
    "ctransid" / cs.Int64ul,
    # trans when created
    "otransid" / cs.Int64ul,
    # trans when sent. non-zero for received subvol
    "stransid" / cs.Int64ul,
    # trans when received. non-zero for received subvol
    "rtransid" / cs.Int64ul,
    "ctime" / Timespec,
    "otime" / Timespec,
    "stime" / Timespec,
    "rtime" / Timespec,
    "reserved" / cs.Int64ul[8],
    )


RootRef = Struct(
    "dirid" / cs.Int64ul * "ID of directory in [tree id] that contains the subtree",
    "sequence" / cs.Int64ul * "Sequence (index in tree) (even, starting at 2?)",
    "name_len" / cs.Int16ul,
    "name" / cs.PaddedString(cs.this.name_len, 'ascii'),
    )


DevItem = Struct(
    "devid" / cs.Int64ul,
    "total_bytes" / cs.Int64ul,
    "bytes_used" / cs.Int64ul,
    "io_align" / cs.Int32ul,
    "io_width" / cs.Int32ul,
    "sector_size" / cs.Int32ul,
    "type" / cs.Int64ul,
    "generation" / cs.Int64ul,
    "start_offset" / cs.Int64ul,
    "dev_group" / cs.Int32ul,
    "seek_speed" / cs.Int8ul,
    "bandwidth" / cs.Int8ul,
    "uuid" / UUID,
    "fsid" / FSID,
    )


SuperFlags = cs.FlagsEnum(
    cs.Int64ul,
    ERROR=1 << 2,
    SEEDING=1 << 32,
    METADUMP=1 << 33,
    METADUMP_V2=1 << 34,
    CHANGING_FSID=1 << 35,
    CHANGING_FSID_V2=1 << 36,
)


Superblock = Struct(
    "csum" / cs.Hex(cs.Bytes(BTRFS_CSUM_SIZE)),
    "fsid" / FSID,
    "bytenr" / cs.Int64ul,
    "flags" / SuperFlags,
    "magic" / cs.Const(BTRFS_MAGIC),
    "generation" / cs.Int64ul,
    #: Logical address of the root tree root
    "root" / cs.Int64ul,
    #: Logical address of the chunk tree root
    "chunk_root" / cs.Int64ul,
    #: Logical address of the log tree root
    "log_root" / cs.Int64ul,
    "log_root_transid" / cs.Int64ul,
    "total_bytes" / cs.Int64ul,
    "bytes_used" / cs.Int64ul,
    "root_dir_objectid" / cs.Int64ul,
    "num_devices" / cs.Int64ul,
    "sector_size" / cs.Int32ul,
    "node_size" / cs.Int32ul,
    #: Unused and must be equal to `nodesize`
    "leafsize" / cs.Int32ul,
    "stripesize" / cs.Int32ul,
    "sys_chunk_array_size" / cs.Int32ul,
    "chunk_root_generation" / cs.Int64ul,
    "compat_flags" / cs.Int64ul,
    "compat_ro_flags" / cs.Int64ul,
    "incompat_flags" / cs.Int64ul,
    "csum_type" / cs.Int16ul,
    "root_level" / cs.Int8ul,
    "chunk_root_level" / cs.Int8ul,
    "log_root_level" / cs.Int8ul,
    "dev_item" / DevItem,
    "label" / cs.PaddedString(BTRFS_LABEL_SIZE, 'utf8'),
    "cache_generation" / cs.Int64ul,
    "uuid_tree_generation" / cs.Int64ul,
    "metadata_uuid" / UUID,
    #: Future expansion
    "_reserved" / cs.Int64ul[28],
    "sys_chunks" / SysChunk[1],
    )
