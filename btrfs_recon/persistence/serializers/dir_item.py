from marshmallow import fields

from btrfs_recon import structure
from btrfs_recon.persistence import DirItem
from btrfs_recon.persistence.serializers import KeySchema, LeafItemDataSchema

__all__ = [
    'DirItemSchema',
]


class DirItemSchema(LeafItemDataSchema):
    class Meta:
        model = DirItem
        struct_class = structure.DirItem
        key_type = structure.KeyType.DirItem

    location = fields.Nested(KeySchema)
