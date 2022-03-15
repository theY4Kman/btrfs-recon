from btrfs_recon import structure
from btrfs_recon.persistence import models
from .base import LeafItemDataSchema

__all__ = [
    'InodeItemSchema',
    'InodeRefSchema',
]


class InodeItemSchema(LeafItemDataSchema):
    class Meta:
        model = models.InodeItem
        struct_class = structure.InodeItem
        key_type = structure.KeyType.InodeItem


class InodeRefSchema(LeafItemDataSchema):
    class Meta:
        model = models.InodeRef
        struct_class = structure.InodeRef
        key_type = structure.KeyType.InodeRef
