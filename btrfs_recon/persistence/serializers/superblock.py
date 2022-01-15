from btrfs_recon import structure
from btrfs_recon.persistence import DevItem, Superblock, SysChunk
from . import fields
from .base import StructSchema

__all__ = [
    'DevItemSchema',
    'SysChunkSchema',
    'SuperblockSchema',
]


class DevItemSchema(StructSchema):
    class Meta:
        model = DevItem
        struct_class = structure.DevItem


class SysChunkSchema(StructSchema):
    class Meta:
        model = SysChunk
        struct_class = structure.SysChunk

    key = fields.Nested('KeySchema')
    chunk = fields.Nested('ChunkItemSchema')


class SuperblockSchema(StructSchema):
    class Meta:
        model = Superblock
        struct_class = structure.Superblock

    dev_item = fields.Nested(DevItemSchema)
    sys_chunks = fields.Nested(SysChunkSchema, many=True)
