from btrfs_recon import structure
from btrfs_recon.persistence import models
from .base import StructSchema

__all__ = [
    'FileExtentItemSchema',
]


class FileExtentItemSchema(StructSchema):
    class Meta:
        model = models.FileExtentItem
        struct_class = structure.FileExtentItem
        key_type = structure.KeyType.ExtentData
