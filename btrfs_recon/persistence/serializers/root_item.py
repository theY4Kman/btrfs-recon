import marshmallow as ma
from btrfs_recon import structure
from btrfs_recon.persistence import RootItem
from btrfs_recon.persistence.serializers import KeySchema, LeafItemDataSchema

from . import fields

__all__ = [
    'RootItemSchema',
]


def get_root_item_inode_schema():
    from btrfs_recon.persistence.serializers import InodeItemSchema

    class RootItemInodeSchema(InodeItemSchema):
        class Meta:
            exclude = ('leaf_item',)
        root_item = fields.ParentInstanceField()

    return RootItemInodeSchema


class RootItemSchema(LeafItemDataSchema):
    class Meta:
        model = RootItem
        struct_class = structure.RootItem
        key_type = structure.KeyType.RootItem

    inode = fields.Nested(get_root_item_inode_schema)
    drop_progress = fields.Nested(KeySchema)

    @ma.pre_load
    def before_load(self, data, **kwargs):
        # Don't create drop_progress Key if zeroed out
        if 'drop_progress' in data and not data['drop_progress']:
            del data['drop_progress']
        return data
