from marshmallow import fields

from btrfs_recon.persistence import DevItem, Superblock, SysChunk
from .base import StructSchema

__all__ = [
    'DevItemSchema',
    'SysChunkSchema',
    'SuperblockSchema',
]


class DevItemSchema(StructSchema):
    class Meta:
        model = DevItem


class SysChunkSchema(StructSchema):
    class Meta:
        model = SysChunk

    chunk = fields.Nested('btrfs_recon.persistence.serializers.chunk_item.ChunkItemSchema')


class SuperblockSchema(StructSchema):
    class Meta:
        model = Superblock

    dev_item = fields.Nested(DevItemSchema)
    sys_chunks = fields.Nested(SysChunkSchema, many=True)
