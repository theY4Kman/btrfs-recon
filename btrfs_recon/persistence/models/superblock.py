from typing import Any, TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy.orm as orm

from btrfs_recon import structure
from btrfs_recon.persistence import fields
from .base_node import BaseNode
from .key import Keyed

if TYPE_CHECKING:
    from .physical import Device

__all__ = [
    'Superblock',
    'SysChunk',
]


class Superblock(BaseNode):
    csum = sa.Column(pg.BYTEA, nullable=False)
    fsid = sa.Column(pg.UUID, nullable=False)

    flags = sa.Column(fields.uint8, nullable=False)
    generation = sa.Column(fields.uint8, nullable=False)

    root = sa.Column(fields.uint8, nullable=False)
    chunk_root = sa.Column(fields.uint8, nullable=False)
    log_root = sa.Column(fields.uint8, nullable=False)
    log_root_transid = sa.Column(fields.uint8, nullable=False)

    total_bytes = sa.Column(fields.uint8, nullable=False)
    bytes_used = sa.Column(fields.uint8, nullable=False)

    root_dir_objectid = sa.Column(fields.uint8, nullable=False)
    num_devices = sa.Column(fields.uint8, nullable=False)
    sector_size = sa.Column(fields.uint4, nullable=False)
    node_size = sa.Column(fields.uint4, nullable=False)
    leafsize = sa.Column(fields.uint4, nullable=False)
    stripesize = sa.Column(fields.uint4, nullable=False)

    sys_chunk_array_size = sa.Column(fields.uint4, nullable=False)

    chunk_root_generation = sa.Column(fields.uint8, nullable=False)
    compat_flags = sa.Column(fields.uint8, nullable=False)
    compat_ro_flags = sa.Column(fields.uint8, nullable=False)
    incompat_flags = sa.Column(fields.uint8, nullable=False)

    csum_type = sa.Column(fields.uint2, nullable=False)
    root_level = sa.Column(fields.uint1, nullable=False)
    chunk_root_level = sa.Column(fields.uint1, nullable=False)
    log_root_level = sa.Column(fields.uint1, nullable=False)

    label = sa.Column(sa.String, nullable=False)
    cache_generation = sa.Column(fields.uint8, nullable=False)
    uuid_tree_generation = sa.Column(fields.uint8, nullable=False)
    metadata_uuid = sa.Column(pg.UUID, nullable=False)

    dev_item_id = sa.Column(sa.ForeignKey('dev_item.id'), nullable=False)
    dev_item = orm.relationship('DevItem')

    sys_chunks = orm.relationship('SysChunk')

    @classmethod
    def parse_struct(cls, device: 'Device', superblock: structure.Superblock, /) -> dict[str, Any]:
        from .dev_item import DevItem
        return {
            **super().parse_struct(device, superblock),

            'csum': superblock.csum,
            'fsid': superblock.fsid,
            'flags': superblock.flags,
            'generation': superblock.generation,
            'root': superblock.root,
            'chunk_root': superblock.chunk_root,
            'log_root': superblock.log_root,
            'log_root_transid': superblock.log_root_transid,
            'total_bytes': superblock.total_bytes,
            'bytes_used': superblock.bytes_used,
            'root_dir_objectid': superblock.root_dir_objectid,
            'num_devices': superblock.num_devices,
            'sector_size': superblock.sector_size,
            'node_size': superblock.node_size,
            'leafsize': superblock.leafsize,
            'stripesize': superblock.stripesize,
            'sys_chunk_array_size': superblock.sys_chunk_array_size,
            'chunk_root_generation': superblock.chunk_root_generation,
            'compat_flags': superblock.compat_flags,
            'compat_ro_flags': superblock.compat_ro_flags,
            'incompat_flags': superblock.incompat_flags,
            'csum_type': superblock.csum_type,
            'root_level': superblock.root_level,
            'chunk_root_level': superblock.chunk_root_level,
            'log_root_level': superblock.log_root_level,
            'label': superblock.label,
            'cache_generation': superblock.cache_generation,
            'uuid_tree_generation': superblock.uuid_tree_generation,
            'metadata_uuid': superblock.metadata_uuid,
            'dev_item': DevItem(
                devid=superblock.dev_item.devid,
                total_bytes=superblock.dev_item.total_bytes,
                bytes_used=superblock.dev_item.bytes_used,
                io_align=superblock.dev_item.io_align,
                io_width=superblock.dev_item.io_width,
                sector_size=superblock.dev_item.sector_size,
                type=superblock.dev_item.type,
                generation=superblock.dev_item.generation,
                start_offset=superblock.dev_item.start_offset,
                dev_group=superblock.dev_item.dev_group,
                seek_speed=superblock.dev_item.seek_speed,
                bandwidth=superblock.dev_item.bandwidth,
                uuid=superblock.dev_item.uuid,
                fsid=superblock.dev_item.fsid,
            ),
            'sys_chunks': [
                SysChunk.from_struct(device, sys_chunk)
                for sys_chunk in superblock.sys_chunks
            ],
        }


class SysChunk(Keyed, BaseNode):
    superblock_id = sa.Column(sa.ForeignKey(Superblock.id), nullable=False)
    superblock = orm.relationship(Superblock)

    chunk_id = sa.Column(sa.ForeignKey('chunk_item.id'), nullable=False)
    chunk = orm.relationship('Chunk')

    @classmethod
    def parse_struct(cls, device: 'Device', sys_chunk: structure.SysChunk, /) -> dict[str, Any]:
        from .chunk_item import ChunkItem
        return dict(**sys_chunk.key, chunk=ChunkItem.from_struct(device, sys_chunk.chunk))
