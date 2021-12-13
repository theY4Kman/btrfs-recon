import io
import uuid
from collections import deque
from pathlib import Path
from typing import BinaryIO

import construct as cs
from construct_typed import csfield
from intervaltree import Interval, IntervalTree

BTRFS_MAGIC: bytes = b"_BHRfS_M"
BTRFS_UUID_SIZE: int = 16
BTRFS_LABEL_SIZE: int = 256
BTRFS_CSUM_SIZE: int = 32
BTRFS_FSID_SIZE: int = 16


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
    DevItems=1,
    BtreeInode=1,
    EmptySubvolDir=2,
)

CsumType = cs.Enum(
    cs.Int16ul,
    crc32=0,
    xxhash=1,
    sha256=2,
    blake2=3,
)


Key = cs.Struct(
    "objectid" / ObjectId,
    "ty" / KeyType,
    "offset" / cs.Int64ul,
)


Stripe = cs.Struct(
    "devid" / cs.Int64ul,
    "offset" / cs.Int64ul,
    "dev_uuid" / UUID,
)


Chunk = cs.Struct(
    "length" / cs.Int64ul,
    "owner" / cs.Int64ul,
    "stripe_len" / cs.Int64ul,
    "ty" / cs.Int64ul,
    "io_align" / cs.Int32ul,
    "io_width" / cs.Int32ul,
    "sector_size" / cs.Int32ul,
    "num_stripes" / cs.Int16ul,
    "sub_stripes" / cs.Int16ul,
    "stripes" / Stripe[cs.this.num_stripes],
)


SysChunk = cs.Struct(
    "key" / Key,
    "chunk" / Chunk,
)

Header = cs.Struct(
    "csum" / cs.Hex(cs.Bytes(BTRFS_CSUM_SIZE)),
    "fsid" / FSID,
    "bytenr" / cs.Int64ul,
    "flags" / cs.Int64ul,
    "chunk_tree_uuid" / UUID,
    "generation" / cs.Int64ul,
    "owner" / cs.Int64ul,
    "nritems" / cs.Int32ul,
    "level" / cs.Int8ul,
)


KeyPtr = cs.Struct(
    "key" / Key,
    "blockptr" / cs.Int64ul,
    "generation" / cs.Int64ul,
)


Item = cs.Struct(
    "key" / Key,
    "offset" / cs.Int32ul,
    "size" / cs.Int32ul,
)


ChunkTreeItem = cs.Struct(
    "header" / Header,
    "items" / cs.IfThenElse(
        cs.this.header.level == 0,
        Item[cs.this.header.nritems],
        KeyPtr[cs.this.header.nritems],
    ),
)


Timespec = cs.Struct(
    "sec" / cs.Int64ul,
    "nsec" / cs.Int32ul,
)


InodeItem = cs.Struct(
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
    "flags" / cs.Int64ul,

    # modification sequence number for NFS
    "sequence" / cs.Int64ul,

    "reserved" / cs.Int64ul[4],
    "atime" / Timespec,
    "ctime" / Timespec,
    "mtime" / Timespec,
    "otime" / Timespec,
)


RootItem = cs.Struct(
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


DevItem = cs.Struct(
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


Superblock = cs.Struct(
    "csum" / cs.Hex(cs.Bytes(BTRFS_CSUM_SIZE)),
    "fsid" / FSID,
    "bytenr" / cs.Int64ul,
    "flags" / cs.Int64ul,
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


class ChunkTreeCache(IntervalTree):
    def insert(self, logical: int, size: int, physical: int):
        """Record a mapping of logical -> physical for a block of logical address space"""
        self.addi(logical, logical + size, physical)

    def offset(self, logical: int) -> int:
        """Return the mapped physical address for the given logical address

        This method will offset the physical address if the logical address is in the middle of a
        mapped block.
        """
        blocks: set[Interval] = self.at(logical)
        assert len(blocks) <= 1, \
            f'Multiple logical blocks matched {logical}. This should never happen.'

        if not blocks:
            raise KeyError(f'Unable to find physical address mapping for logical address {logical}')

        block = next(iter(blocks))
        offset = logical - block.begin
        physical = block.data + offset
        return physical


def parse_superblock(fs: BinaryIO) -> Superblock:
    superblock = cs.Pointer(0x10000, Superblock).parse_stream(fs)

    tree = ChunkTreeCache()
    for sys_chunk in superblock.sys_chunks:
        tree.insert(
            sys_chunk.key.offset,
            sys_chunk.chunk.length,
            sys_chunk.chunk.stripes[0].offset,
        )

    chunk_root_physical = tree.offset(superblock.chunk_root)
    chunk_tree_queue = deque((chunk_root_physical,))
    while chunk_tree_queue:
        physical = chunk_tree_queue.popleft()
        chunk_tree_item = cs.Pointer(physical, ChunkTreeItem).parse_stream(fs)

        print(f'=== CHUNK TREE ITEM: {hex(physical)} ({physical})')
        print(chunk_tree_item)
        print(f'===')
        print()

        # Leaf node
        if chunk_tree_item.header.level == 0:
            for item in chunk_tree_item['items']:
                if item.key.ty != KeyType.ChunkItem:
                    continue

                chunk_physical = physical + Header.sizeof() + item.offset
                chunk = cs.Pointer(chunk_physical, Chunk).parse_stream(fp)
                tree.insert(
                    item.key.offset,
                    chunk.length,
                    chunk.stripes[0].offset,
                )

                print(f'=== CHUNK: {hex(chunk_physical)} ({chunk_physical})')
                print(chunk)
                print(f'===')
                print()

        # Internal node (level != 0)
        else:
            for ptr in chunk_tree_item['items']:
                node_physical = tree.offset(ptr.blockptr)
                chunk_tree_queue.append(node_physical)

    root_tree_root_physical = tree.offset(superblock.root)
    root_tree_queue = deque((root_tree_root_physical,))
    while root_tree_queue:
        physical = root_tree_queue.popleft()
        root_tree_item = cs.Pointer(physical, Header).parse_stream(fs)
        print(physical)
        print(root_tree_item)

    return superblock


if __name__ == '__main__':
    ssd = Path('/mnt/nas/Disk Image of SSD btrfs (2021-12-02 2142).img')
    nvme = Path('/mnt/nas/Disk Image of nvme0n1 (2021-12-02 2146).img')
    image_1 = Path('/home/they4kman/programming/personal/btrfs-recon/image_1')
    image_2 = Path('/home/they4kman/programming/personal/btrfs-recon/image_2')

    print('= NVMe ==============')
    with nvme.open('rb') as fp:
        print(parse_superblock(fp))
    print()
    print()
