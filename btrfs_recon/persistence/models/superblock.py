from typing import Any, TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy.orm as orm

from btrfs_recon import structure
from btrfs_recon.persistence import fields
from .base import BaseStruct
from .key import Keyed

if TYPE_CHECKING:
    from .physical import Device

__all__ = [
    'Superblock',
    'SysChunk',
]


class Superblock(BaseStruct):
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

    sys_chunks = orm.relationship('SysChunk', back_populates='superblock')


class SysChunk(Keyed, BaseStruct):
    superblock_id = sa.Column(sa.ForeignKey(Superblock.id), nullable=False)
    superblock = orm.relationship(Superblock)

    chunk_id = sa.Column(sa.ForeignKey('chunk_item.id'), nullable=False)
    chunk = orm.relationship('ChunkItem')
