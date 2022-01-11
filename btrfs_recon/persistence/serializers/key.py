from btrfs_recon import structure
from btrfs_recon.persistence import models
from btrfs_recon.persistence.serializers import fields, StructSchema

__all__ = [
    'KeySchema',
]


class KeySchema(StructSchema):
    class Meta:
        model = models.Key
        struct_class = structure.Key

    struct = fields.ParentInstanceField()
