import io
import typing
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Callable, Iterable

import construct as cs
import crc32c
from construct_typed import csfield
from intervaltree import Interval, IntervalTree
from tqdm import tqdm

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

# Root!!!!
# 257423802368


def calculate_crc32c_checksum(data: bytes) -> bytes:
    return cs.Int32ub.build(crc32c.crc32c(data)) + b'\0' * (BTRFS_CSUM_SIZE - 4)


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


# _Container_str = cs.Container.__str__
#

# def _labeled_container_str(self) -> str:
#     orig_str = _Container_str(self)
#     try:
#         orig_str[:orig_str.index(':')] = self._label
#     except AttributeError:
#         pass
#     return orig_str
#
#
# cs.Container.__str__ = _labeled_container_str
# _Struct_name_registry = {}
#
#
#
#
# def _add_labels_to_structs():
#     for name, value in globals().items():
#         if isinstance(value, Struct):
#             value.subcons.append('_label' / cs.Consname
#
#
# _add_labels_to_structs()


DevId = int
PhysicalAddress = int


class ChunkTreeCache(IntervalTree):
    def insert(
        self,
        logical: int,
        size: int,
        stripes: Iterable[tuple[DevId, PhysicalAddress]] | dict[DevId, PhysicalAddress] | Iterable[cs.Container]
    ) -> Interval:
        """Record a mapping of logical -> physical for a block of logical address space"""
        if not isinstance(stripes, dict):
            stripes = tuple(stripes)
            assert stripes

            if isinstance(stripes[0], cs.Container):
                stripes = {stripe.devid: stripe.offset for stripe in stripes}

        begin = logical
        end = begin + size
        if matches := self[begin:end]:
            assert len(matches) == 1
            ival, = matches
            ival.data.update(stripes)
        else:
            ival = Interval(begin, end, dict(stripes))
            self.add(ival)

        return ival

    def offsets(self, logical: int) -> dict[DevId, PhysicalAddress]:
        """Return the mapped physical addresses for the given logical address

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
        return {
            devid: physical_start + offset
            for devid, physical_start in block.data.items()
        }


# class BtrfsVolume:
#     def __init__(self):


def parse_fs(*device_handles: BinaryIO) -> tuple[Superblock, ChunkTreeCache]:
    if not device_handles:
        raise ValueError('Please pass at least one device/image file handle')

    devid_fp_map = {}
    for fp in device_handles:
        superblock = cs.Pointer(0x10000, Superblock).parse_stream(fp)
        dev_item = superblock.dev_item
        devid_fp_map[dev_item.devid] = fp

    tree = ChunkTreeCache()
    for sys_chunk in superblock.sys_chunks:
        tree.insert(
            sys_chunk.key.offset,
            sys_chunk.chunk.length,
            sys_chunk.chunk.stripes,
        )

    chunk_tree_queue: deque[tuple[DevId, PhysicalAddress]] = deque(tree.offsets(superblock.chunk_root).items())
    while chunk_tree_queue:
        devid, physical = chunk_tree_queue.popleft()
        fp = devid_fp_map[devid]
        node = cs.Pointer(physical, TreeNode).parse_stream(fp)

        # print(f'=== CHUNK TREE ITEM: {hex(physical)} ({physical})')
        # print(chunk_tree_item)
        # print(f'===')
        # print()

        # Leaf node
        if node.header.level == 0:
            for item in node['items']:
                if item.key.ty != KeyType.ChunkItem:
                    continue

                tree.insert(
                    item.key.offset,
                    item.data.length,
                    item.data.stripes,
                )

                # print(f'=== CHUNK: {hex(chunk_physical)} ({chunk_physical})')
                # print(chunk)
                # print(f'===')
                # print()

        # Internal node (level != 0)
        else:
            for ptr in node['items']:
                node_physical = tree.offset(ptr.blockptr)
                chunk_tree_queue.append(node_physical)

    # root_tree_root_physical = tree.offset(superblock.root)
    # root_tree_queue = deque((root_tree_root_physical,))
    # while root_tree_queue:
    #     physical = root_tree_queue.popleft()
    #     root_tree_item = cs.Pointer(physical, Header).parse_stream(fs)
    #     print(physical)
    #     print(root_tree_item)

    return superblock, tree


def parse_at(fp, pos, type_, **contextkw):
    return cs.Pointer(pos, type_).parse_stream(fp, **contextkw)


def pparse_at(fp, pos, type_, **contextkw):
    print(parse_at(fp, pos, type_, **contextkw))


def walk_fs_tree(root: TreeNode):
    print(root)


class FindNodesLogFunc(typing.Protocol):
    def __call__(
        self,
        *values: object,
        sep: str | None = ...,
        end: str | None = ...,
        file: typing.TextIO | None = ...,
        flush: bool = ...,
    ) -> None: ...


def find_nodes(
    fp: io.FileIO, *,
    alignment: int = 0x10000,
    start_loc: int | None = None,
    reversed: bool = True,
    fsid: str | int | bytes | uuid.UUID | None = uuid.UUID('bba692f7-5be7-4173-bc27-bb3e21644739'),
    predicate: Callable[[int, Header], bool] | None = None,
    echo: bool = True,
    show_progress: bool = True,
) -> tuple[FindNodesLogFunc, Iterable[tuple[int, Header]]]:
    if fsid is not None and not isinstance(fsid, uuid.UUID):
        fsid = uuid.UUID(fsid)

    fp.seek(0, io.SEEK_END)
    file_size = fp.tell()
    max_loc = file_size - Header.sizeof()
    aligned_max_loc = max_loc - (max_loc % alignment)

    max_hex_length = len(f'0x{file_size:x}')
    max_int_length = len(f'{file_size}')

    if reversed:
        start_loc = aligned_max_loc if start_loc is None else start_loc
        loc_iter = range(start_loc, -1, -alignment)
    else:
        start_loc = 0 if start_loc is None else start_loc
        loc_iter = range(start_loc, aligned_max_loc + 1, alignment)

    if show_progress:
        pbar = tqdm(loc_iter, unit='loc')
        buf = io.StringIO()

        def log(*args, **kwargs):
            end = kwargs.pop('end', '\n')
            sep = kwargs.pop('sep', ' ')
            print(*args, end=end, sep=sep, file=buf)
            pbar.write(buf.getvalue(), end='', **kwargs)
            buf.seek(0)
            buf.truncate()
    else:
        pbar = loc_iter
        log = print

    def find_results() -> Iterable[tuple[int, Header]]:
        for loc in pbar:
            header = parse_at(fp, loc, Header)
            if fsid is not None and header.fsid != fsid:
                continue

            if predicate is not None and not predicate(loc, header):
                continue

            if echo:
                log(f'0x{loc:0{max_hex_length}x} ({loc:>{max_int_length}d})')

            yield loc, header

    return log, find_results()


def find_fs_roots(fp: io.FileIO, **kwargs) -> Iterable[tuple[int, Item]]:
    log, results = find_nodes(
        fp, **kwargs, predicate=lambda loc, header: header.level == 0 and header.nritems > 0
    )

    for loc, header in results:
        node = parse_at(fp, loc, TreeNode)
        for item in reversed(node['items']):
            if not (
                item.key.objectid == ObjectId.FsTree
                and item.key.ty == KeyType.RootItem
            ):
                continue

            log(f'\n\n!!!!!!!! FOUND ROOT TREE ITEM !!!!!!!!!!!!!')
            log(f'### Header — {hex(loc)} (loc)')
            log(str(header))
            log(f'\n')
            log(f'### Item')
            log(str(item))
            log('')
            log('')

            yield loc, item


if __name__ == '__main__':
    ssd = Path('/mnt/nas/Disk Image of SSD btrfs (2021-12-02 2142).img')
    nvme = Path('/home/they4kman/BTRFS-IMAGES/Disk Image of nvme0n1 (2021-12-02 2146).img')
    image_1 = Path('/home/they4kman/programming/personal/btrfs-recon/image_1')
    image_2 = Path('/home/they4kman/programming/personal/btrfs-recon/image_2')

    with nvme.open('rb') as nvme_fp, ssd.open('rb') as ssd_fp:
        superblock, tree = parse_fs(nvme_fp, ssd_fp)
        # print(superblock)
        #
        # possible_roots = [
        #     0xabfeaa0000,
        #     0xabf21a0000,
        #     # 0xabc1740000,  # wrong fsid — seems garble
        #     0x898f000000,
        #     0x8980210000,
        #     0x893ab30000,
        #     0x89299d0000,
        #     0x8920ae0000,
        #     0x891a890000,
        #     0x8918570000,
        #     0x8901a10000,
        #     0x743a7b0000,
        #     0x7411c40000,
        #     0x7407090000,
        #     0x58c2a00000,
        #     0x38724f0000,
        #     0x383a1a0000,
        #     0x3836be0000,
        # ]
        # root_items = {}
        # fs_roots = {}
        # for root_physical in reversed(possible_roots):
        #     root = root_items[root_physical] = parse_at(fp, root_physical, TreeNode)
        #     item_types = {f'{item.key.ty}({item.key.objectid})' for item in root['items']}
        #     print()
        #     print(
        #         f'[gen={root.header.generation:>7}]'
        #         f'[nritems={root.header.nritems:>3}] '
        #         f'logical {root.header.bytenr:>10x} => physical {root_physical:>10x} '
        #         f'{{ {", ".join(item_types)} }}'
        #     )
        #
        #     fs_root_item = next(
        #         item
        #         for item in root['items']
        #         if item.key.ty == KeyType.RootItem and item.key.objectid == ObjectId.FsTree
        #     )
        #     fs_root_phys = tree.offset(fs_root_item.data.bytenr)
        #     fs_root_header = parse_at(fp, fs_root_phys, Header)
        #
        #     if fs_root_header.nritems > 200:
        #         fs_root = fs_root_header
        #         print(fs_root)
        #     else:
        #         fs_root = parse_at(fp, fs_root_phys, TreeNode)
        #         walk_fs_tree(fs_root)
        #
        #     fs_roots[root_physical] = fs_root
        #
        #     print()
        #     print()

        #XXX######################################################################################
        # expected_fsid = uuid.UUID('bba692f7-5be7-4173-bc27-bb3e21644739')
        # valid_locs = []
        # # base = 0x74024E4000
        # invalid_locs: set[int] = set()
        #
        # invalid_locs_path = Path('invalid_locs.txt')
        # if invalid_locs_path.exists():
        #     invalid_locs.update(map(int, invalid_locs_path.read_text().strip().splitlines()))
        #
        # def _record_invalid_loc(loc):
        #     invalid_locs.add(loc)
        #     with invalid_locs_path.open('a') as fp:
        #         fp.write(f'{loc}\n')
        #
        # chunk_pbar = tqdm(sorted(tree.all_intervals, key=lambda ival: ival.begin), unit='chunk')
        # for ival in chunk_pbar:
        #     ival: Interval
        #     base = ival.data
        #     end = base + ival.length()
        #
        #     for loc in tqdm(range(base, end + 1, superblock.sector_size), unit='sector', position=1):
        #         if loc in invalid_locs:
        #             continue
        #
        #         try:
        #             header = parse_at(fp, loc, Header)
        #         except cs.ValidationError:
        #             _record_invalid_loc(loc)
        #             continue
        #         else:
        #             if header.fsid != expected_fsid:
        #                 _record_invalid_loc(loc)
        #                 continue
        #
        #         try:
        #             node = parse_at(fp, loc, TreeNode)
        #         except cs.ValidationError:
        #             _record_invalid_loc(loc)
        #             continue
        #
        #         chunk_pbar.write(str(node))
        #         valid_locs.append(loc)
        #         chunk_pbar.write('')
        #         chunk_pbar.write('')
        #
        # print()
        # print()
        # print('Valid locs:')
        # print('\n'.join(hex(v) for v in valid_locs))
        # print()
        # print('# valid locs:', len(valid_locs))
        #XXX######################################################################################

    print()
    print()
