import marshmallow as ma

from btrfs_recon import structure
from btrfs_recon.persistence import models
from .base import LeafItemDataSchema

__all__ = [
    'FileExtentItemSchema',
]


class FileExtentItemSchema(LeafItemDataSchema):
    class Meta:
        model = models.FileExtentItem
        struct_class = structure.FileExtentItem
        key_type = structure.KeyType.ExtentData
        version = 1

    @ma.pre_load
    def before_load(self, data, **kwargs):
        # Because marshmallow, for whatever reason, doesn't support deep data_keys
        # (i.e. dotted paths), we raise our ref.* keys to toplevel.
        if data['ref']:
            data.update(data['ref'])

        return data
